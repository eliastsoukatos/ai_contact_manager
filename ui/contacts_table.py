from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QInputDialog,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QApplication,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtGui import QBrush
from PyQt5.QtCore import Qt, QPoint, QObject, QThread, pyqtSignal, pyqtSlot

import os

from db_manager import DBManager
from config.settings import get_settings, save_settings, update_setting
from ui.filter_popup import FilterPopup
from ui.filter_header import FilterHeader
from ui.tag_tools import TagSelectionDialog, ModeIndicator, TagsCellWidget
from ui.export_dialog import ExportOptionsDialog
from exporter import export_contacts
from utils import (
    disposition_to_status,
    disposition_to_color,
    status_to_color,
    clean_phone_number,
)


class FetchContactsWorker(QObject):
    """Worker object to fetch contacts in a background thread."""

    finished = pyqtSignal(list)

    def __init__(self, db, filters=None, search="", sort_by="", sort_order="asc"):
        super().__init__()
        self._db = db
        self._filters = filters
        self._search = search
        self._sort_by = sort_by
        self._sort_order = sort_order

    @pyqtSlot()
    def run(self):
        contacts = self._db.fetch_contacts(
            filters=self._filters,
            search=self._search,
            sort_by=self._sort_by,
            sort_order=self._sort_order,
        )
        self.finished.emit(contacts)


class ContactsTableWidget(QWidget):
    """Widget displaying contacts with filtering and batch actions."""

    HEADERS = [
        "mobile",
        "first_name",
        "last_name",
        "email",
        "company_name",
        "company_alias",
        "website",
        "country",
        "state",
        "city",
        "morning_call_time",
        "afternoon_call_time",
        "target_company",
        "contact_icp_status",
        "clients_of_contact",
        "area_of_business",
        "most_relevant_summit",
        "client_icp",
        "time_zone_utc",
        "job_title",
        "personal_linkedin_url",
        "contact_disposition",
        "tags",
        "status",
    ]

    def __init__(self, db: DBManager, status_callback=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._status_callback = status_callback or (lambda *args, **kwargs: None)
        self.contacts = []
        self.filtered_contacts = []
        self.search_text = ""
        self.column_visibility = {h: True for h in self.HEADERS}
        self.filters = {}
        self.sort_column = None
        self.sort_order = Qt.AscendingOrder
        self.quick_mode = None
        self.quick_tag = ""
        self.session_tags = set()
        self._value_cache = {}
        self._fetch_thread = None
        self._load_layout()
        self._setup_ui()
        self.load_contacts()

    def _start_worker(self, worker, callback):
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(callback)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        return thread

    def _fetch_contacts_async(
        self,
        callback,
        filters=None,
        search="",
        sort_by="",
        sort_order="asc",
    ):
        worker = FetchContactsWorker(
            self.db,
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return self._start_worker(worker, callback)

    def _set_disposition_style(self, combo: QComboBox, disposition: str):
        """Apply background color to the disposition combo box."""
        color = disposition_to_color(disposition)
        if color:
            combo.setStyleSheet(f"QComboBox{{background-color: {color};}}")
        else:
            combo.setStyleSheet("")

    def _set_status_style(self, combo: QComboBox, status: str):
        """Apply background color to the status combo box."""
        color = status_to_color(status)
        if color:
            combo.setStyleSheet(f"QComboBox{{background-color: {color};}}")
        else:
            combo.setStyleSheet("")

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.mode_indicator = ModeIndicator(self._exit_quick_mode)
        self.mode_indicator.hide()
        layout.addWidget(self.mode_indicator)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        header = FilterHeader()
        self.table.setHorizontalHeader(header)
        header.setSectionsMovable(True)
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellDoubleClicked.connect(self._handle_cell_double_clicked)
        self.table.setSortingEnabled(False)
        header.setSectionsClickable(True)
        header.filter_requested.connect(self._open_filter_popup)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_filter_context)
        self._filter_header = header
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)

        self._apply_layout()

    def load_contacts(self):
        self._apply_filters()
        self._refresh_value_cache()

    def set_search_text(self, text: str):
        self.search_text = text
        self._apply_filters()


    def _apply_filters(self):
        sort_by = ""
        if self.sort_column is not None:
            sort_by = self.HEADERS[self.sort_column]
        sort_order = "desc" if self.sort_order == Qt.DescendingOrder else "asc"
        # Ignore filters belonging to hidden columns so they don't affect the
        # visible results. This avoids confusion if a hidden column still has an
        # active filter without permanently discarding the user's selection.
        visible_filters = {
            k: v
            for k, v in self.filters.items()
            if self.column_visibility.get(k, True)
        }
        filters = {k: list(v) for k, v in visible_filters.items()}
        if self._fetch_thread:
            self._fetch_thread.quit()
            self._fetch_thread.wait()

        def _on_fetched(contacts):
            self.contacts = contacts
            self._show_contacts(contacts)

        self._fetch_thread = self._fetch_contacts_async(
            _on_fetched,
            filters=filters,
            search=self.search_text,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def _show_contacts(self, contacts):
        self.filtered_contacts = contacts
        self.table.blockSignals(True)
        self.table.setRowCount(len(contacts))
        for row, contact in enumerate(contacts):
            for col, header in enumerate(self.HEADERS):
                if header == "contact_disposition":
                    combo = QComboBox()
                    dispositions = [
                        "not_defined",
                        "connected_positive",
                        "connected_meeting_booked",
                        "connected_neutral",
                        "connected_negative",
                        "wrong_number",
                        "not_in_service",
                        "number_validated",
                        "left_voicemail",
                        "no_answer",
                        "do_not_call",
                        "referred_to_another_contact",
                        "busy_call_back_later",
                        "unreachable",
                        "wrong_company",
                    ]
                    combo.addItems(dispositions)
                    current_disp = contact.get("contact_disposition", "")
                    combo.setCurrentText(current_disp)
                    self._set_disposition_style(combo, current_disp)
                    combo.currentTextChanged.connect(
                        lambda value, cid=contact.get("profile_id"), c=combo: (
                            self._on_disposition_changed(cid, value),
                            self._set_disposition_style(c, value),
                        )
                    )
                    self.table.setCellWidget(row, col, combo)
                elif header == "tags":
                    tags = [t for t in str(contact.get("tags", "")).split(",") if t]
                    widget = TagsCellWidget(
                        contact.get("profile_id"), tags, row, self._on_tag_button_clicked
                    )
                    widget.setProperty("raw", contact.get("tags", ""))
                    self.table.setCellWidget(row, col, widget)
                elif header == "status":
                    combo = QComboBox()
                    combo.addItems(["active", "inactive"])
                    current_status = contact.get("status", "")
                    combo.setCurrentText(current_status)
                    self._set_status_style(combo, current_status)
                    combo.currentTextChanged.connect(
                        lambda value, cid=contact.get("profile_id"), c=combo: (
                            self._on_status_changed(cid, value),
                            self._set_status_style(c, value),
                        )
                    )
                    self.table.setCellWidget(row, col, combo)
                elif header in ["website", "personal_linkedin_url"]:
                    value = str(contact.get(header, ""))
                    if value:
                        label = QLabel(f"<a href='{value}'>{value}</a>")
                        label.setOpenExternalLinks(True)
                        label.setProperty("raw", value)
                        label.linkActivated.connect(
                            lambda _url, v=value: self._status_callback(f"Opened {v}")
                        )
                        self.table.setCellWidget(row, col, label)
                    else:
                        self.table.setItem(row, col, QTableWidgetItem(""))
                elif header == "mobile":
                    value = clean_phone_number(str(contact.get("mobile", "")))
                    item = QTableWidgetItem(value)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.table.setItem(row, col, item)
                else:
                    value = str(contact.get(header, ""))
                    item = QTableWidgetItem(value)
                    flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
                    if header in [
                        "target_company",
                        "contact_icp_status",
                        "clients_of_contact",
                        "area_of_business",
                        "most_relevant_summit",
                        "client_icp",
                        "company_alias",
                        "time_zone_utc",
                    ]:
                        flags |= Qt.ItemIsEditable
                        item.setData(Qt.UserRole, contact.get("profile_id"))
                    item.setFlags(flags)
                    self.table.setItem(row, col, item)

            self.table.setColumnHidden(col, not self.column_visibility[header])
        for idx, header in enumerate(self.HEADERS):
            self.table.setColumnHidden(idx, not self.column_visibility[header])
        self.table.blockSignals(False)
        if not getattr(self, "column_widths", {}):
            self.table.resizeColumnsToContents()
        if self.sort_column is not None:
            self.table.sortItems(self.sort_column, self.sort_order)

    def _on_item_changed(self, item):
        header = self.HEADERS[item.column()]
        editable = {
            "tags",
            "target_company",
            "contact_icp_status",
            "clients_of_contact",
            "area_of_business",
            "most_relevant_summit",
            "client_icp",
            "company_alias",
            "time_zone_utc",
        }
        if header not in editable:
            return
        contact_id = item.data(Qt.UserRole)
        if not contact_id:
            return
        self.db.update_contact(contact_id, {header: item.text()})
        self._apply_filters()
        self._refresh_value_cache()
        self._status_callback(f"{header.replace('_', ' ').title()} updated")

    def _on_disposition_changed(self, contact_id, disposition):
        if not contact_id:
            return
        status = disposition_to_status(disposition)
        self.db.update_contact(
            contact_id,
            {"contact_disposition": disposition, "status": status},
        )
        self._apply_filters()
        self._refresh_value_cache()
        self._status_callback("Disposition updated")

    def _on_status_changed(self, contact_id, status):
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"status": status})
        self._apply_filters()
        self._refresh_value_cache()
        self._status_callback("Status updated")

    def _get_all_tags_async(self, callback):
        def _on_contacts(contacts):
            tags = set(self.session_tags)
            for c in contacts:
                tags.update(t.strip() for t in str(c.get("tags", "")).split(",") if t.strip())
            callback(sorted(tags))

        self._fetch_contacts_async(_on_contacts)

    def _batch_add_tag(self):
        def _on_tags(tags):
            dialog = TagSelectionDialog(tags, title="Add Tag to All Visible Contacts", allow_new=True, parent=self)
            if dialog.exec() != QDialog.Accepted:
                return
            tag = dialog.selected_tag()
            if not tag:
                return
            self.session_tags.add(tag)
            for contact in self.filtered_contacts:
                self.db.add_tag(contact.get("profile_id"), tag)
            self._apply_filters()
            self._refresh_value_cache()
            self._status_callback("Tag added")

        self._get_all_tags_async(_on_tags)

    def _batch_remove_tag(self):
        def _on_tags(tags):
            dialog = TagSelectionDialog(tags, title="Remove Tag from All Visible Contacts", allow_new=False, parent=self)
            if dialog.exec() != QDialog.Accepted:
                return
            tag = dialog.selected_tag()
            if not tag:
                return
            for contact in self.filtered_contacts:
                self.db.remove_tag(contact.get("profile_id"), tag)
            self._apply_filters()
            self._refresh_value_cache()
            self._status_callback("Tag removed")

        self._get_all_tags_async(_on_tags)

    def start_quick_tag_mode(self):
        def _on_tags(tags):
            dialog = TagSelectionDialog(tags, title="Select Tag", allow_new=True, parent=self)
            if dialog.exec() != QDialog.Accepted:
                return
            tag = dialog.selected_tag()
            if not tag:
                return
            self.session_tags.add(tag)
            self.quick_mode = "add"
            self.quick_tag = tag
            self.mode_indicator.label.setText(f"Quick Tag mode: {tag}")
            self.mode_indicator.show()
            self._status_callback("Quick Tag mode active")

        self._get_all_tags_async(_on_tags)

    def start_quick_remove_mode(self):
        self.quick_mode = "remove"
        self.quick_tag = ""
        self.mode_indicator.label.setText("Remove Tag mode")
        self.mode_indicator.show()
        self._status_callback("Remove Tag mode active")

    def _exit_quick_mode(self):
        self.quick_mode = None
        self.quick_tag = ""
        self.mode_indicator.hide()
        self._status_callback("Quick mode exited")

    def _batch_set_status(self):
        status, ok = QInputDialog.getItem(
            self,
            "Set Status",
            "Status:",
            ["active", "inactive"],
            editable=False,
        )
        if not ok:
            return
        for contact in self.filtered_contacts:
            self.db.update_contact(contact.get("profile_id"), {"status": status})
        self._apply_filters()
        self._refresh_value_cache()
        self._status_callback("Status updated for selection")

    def _customize_columns(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Customize Columns")
        form = QFormLayout(dialog)
        checkboxes = {}
        for header in self.HEADERS:
            cb = QCheckBox(header)
            cb.setChecked(self.column_visibility[header])
            form.addRow(cb)
            checkboxes[header] = cb
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted:
            for header, cb in checkboxes.items():
                self.column_visibility[header] = cb.isChecked()
            for idx, header in enumerate(self.HEADERS):
                self.table.setColumnHidden(idx, not self.column_visibility[header])
            self._status_callback("Column visibility updated")
            self.save_layout()

    def _open_filter_popup(self, logical):
        header = self.table.horizontalHeader()
        if logical < 0:
            return
        field = self.HEADERS[logical]
        values = self._value_cache.get(field)
        if values is None:
            self._refresh_value_cache()
            values = self._value_cache.get(field, [])

        popup = FilterPopup(values, self)
        if field in self.filters:
            popup.set_selected(self.filters[field])
        popup.selection_changed.connect(
            lambda f=field, p=popup: self._on_filter_changed(f, p)
        )
        popup.sort_requested.connect(
            lambda order, col=logical: self._on_sort_requested(col, order, popup)
        )
        section_left = header.sectionViewportPosition(logical)
        global_pos = header.mapToGlobal(QPoint(section_left, header.height()))
        popup.move(global_pos)
        popup.closed.connect(lambda: self._filter_header.set_active_section(None))
        popup.show()

        self._filter_header.set_active_section(logical)

    def _show_filter_context(self, pos):
        header = self.table.horizontalHeader()
        logical = header.logicalIndexAt(pos)
        self._open_filter_popup(logical)

    def _on_filter_changed(self, field, popup):
        selected = popup.selected_values()
        all_vals = {str(v) for v in popup._all_values}
        if selected == all_vals or not selected:
            self.filters.pop(field, None)
        else:
            self.filters[field] = selected
        self._update_header_styles()
        self._apply_filters()
        self.save_layout()

    def _on_sort_requested(self, column, order, popup):
        self.sort_column = column
        self.sort_order = order
        popup.hide()
        self._apply_filters()
        self.save_layout()

    def _update_header_styles(self):
        for idx, name in enumerate(self.HEADERS):
            item = self.table.horizontalHeaderItem(idx)
            if item is None:
                continue
            font = item.font()
            if name in self.filters:
                item.setBackground(self.palette().highlight())
                font.setBold(True)
            else:
                item.setBackground(QBrush())
                font.setBold(False)
            item.setFont(font)

    def _handle_cell_double_clicked(self, row, column):
        header_view = self.table.horizontalHeader()
        logical = header_view.logicalIndex(column)
        widget = self.table.cellWidget(row, column)
        if widget is not None and hasattr(widget, "property"):
            value = widget.property("raw") or widget.text()
        else:
            item = self.table.item(row, column)
            value = item.text() if item else ""
        if value:
            QApplication.clipboard().setText(value)
            self._status_callback(f"Copied '{value}' to clipboard")

    def _on_cell_clicked(self, row, column):
        if self.quick_mode not in {"add", "remove"}:
            return
        if self.quick_mode == "add":
            if self.HEADERS[column] != "tags":
                return
            contact = self.filtered_contacts[row]
            self.db.add_tag(contact.get("profile_id"), self.quick_tag)
            scroll = self.table.verticalScrollBar().value()
            self._apply_filters()
            self._refresh_value_cache()
            self.table.verticalScrollBar().setValue(scroll)
            self._status_callback("Tag added")

    def _on_tag_button_clicked(self, row, contact_id, tag):
        if self.quick_mode != "remove":
            return
        scroll = self.table.verticalScrollBar().value()
        self.db.remove_tag(contact_id, tag)
        self._apply_filters()
        self._refresh_value_cache()
        self.table.verticalScrollBar().setValue(scroll)
        self._status_callback("Tag removed")

    def _load_layout(self):
        settings = get_settings().get("table_layout", {})
        self.column_visibility.update(settings.get("visibility", {}))
        self.column_order = settings.get("order", self.HEADERS[:])
        self.column_widths = settings.get("widths", {})
        raw_filters = get_settings().get("table_filters", {})
        self.filters = {
            k: set(v) if not isinstance(v, set) else v for k, v in raw_filters.items()
        }
        sort = get_settings().get("table_sort", {})
        column = sort.get("column")
        if column in self.HEADERS:
            self.sort_column = self.HEADERS.index(column)
            self.sort_order = (
                Qt.DescendingOrder if sort.get("order") == "desc" else Qt.AscendingOrder
            )
        if hasattr(self, "table"):
            self._update_header_styles()

    def _apply_layout(self):
        header = self.table.horizontalHeader()
        if hasattr(self, "column_order") and set(self.column_order) == set(self.HEADERS):
            for logical, name in enumerate(self.HEADERS):
                target = self.column_order.index(name)
                header.moveSection(header.visualIndex(logical), target)
        for idx, name in enumerate(self.HEADERS):
            self.table.setColumnHidden(idx, not self.column_visibility.get(name, True))
            if name in getattr(self, "column_widths", {}):
                header.resizeSection(idx, self.column_widths[name])
        self._update_header_styles()

    def save_layout(self):
        header = self.table.horizontalHeader()
        order = [
            self.HEADERS[header.logicalIndex(i)] for i in range(header.count())
        ]
        widths = {
            self.HEADERS[i]: header.sectionSize(i) for i in range(header.count())
        }
        settings = get_settings()
        settings["table_layout"] = {
            "order": order,
            "visibility": self.column_visibility,
            "widths": widths,
        }
        settings["table_filters"] = self.filters
        sort = {}
        if self.sort_column is not None:
            sort = {
                "column": self.HEADERS[self.sort_column],
                "order": "desc" if self.sort_order == Qt.DescendingOrder else "asc",
            }
        settings["table_sort"] = sort
        save_settings()

    def export_view(self):
        """Export the currently visible contacts to CSV."""
        settings = get_settings()
        selected = settings.get("export_fields", self.HEADERS)
        dialog = ExportOptionsDialog(self.HEADERS, selected, self)
        if dialog.exec() != QDialog.Accepted:
            return
        folder, split_by_tz, groups, fields = dialog.options()
        if not folder:
            QMessageBox.warning(self, "Export", "Folder name is required")
            return
        update_setting("export_fields", fields)
        target_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not target_dir:
            return
        export_path = os.path.join(target_dir, folder)
        headers = [h for h in fields if self.column_visibility.get(h, True)]
        files = export_contacts(
            self.filtered_contacts,
            headers,
            export_path,
            groups,
            split_by_tz,
        )
        QMessageBox.information(
            self,
            "Export Complete",
            f"Created {files} file(s) in {export_path}",
        )
        self._status_callback("Export completed")

    def _refresh_value_cache(self):
        """Fetch all contacts and update the unique value cache."""
        contacts = self.db.fetch_contacts()
        cache = {h: set() for h in self.HEADERS}
        for c in contacts:
            for h in self.HEADERS:
                val = c.get(h, "")
                if h == "tags":
                    cache[h].update(t.strip() for t in str(val).split(",") if t.strip())
                else:
                    cache[h].add(str(val))
        self._value_cache = {k: sorted(v) for k, v in cache.items()}




