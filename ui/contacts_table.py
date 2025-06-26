from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QInputDialog,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QApplication,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
)
from PyQt5.QtGui import QBrush
from PyQt5.QtCore import Qt, QPoint

import os

from db_manager import DBManager
from config.settings import get_settings, save_settings, update_setting
from ui.filter_popup import FilterPopup
from ui.filter_header import FilterHeader
from ui.tag_tools import TagSelectionDialog, ModeIndicator, TagsCellWidget
from ui.export_dialog import ExportOptionsDialog
from exporter import export_contacts
from ui.power_up_dialog import PowerUpDialog
from ai.llm_manager import run_prompt, lookup_utc_offset
from ai.enrichment import _calculate_call_times
from utils import (
    disposition_to_status,
    disposition_to_color,
    status_to_color,
    clean_phone_number,
)


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
        settings = get_settings()
        self.page_size = int(settings.get("page_size", 50))
        self.page = 0
        self._has_next = False
        self._load_layout()
        self._setup_ui()
        self.load_contacts()

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

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.page_label = QLabel()
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(1, 1000)
        self.page_size_spin.setValue(self.page_size)
        self.prev_btn.clicked.connect(lambda: self._change_page(-1))
        self.next_btn.clicked.connect(lambda: self._change_page(1))
        self.page_size_spin.editingFinished.connect(self._on_page_size_changed)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.page_label)
        nav.addStretch(1)
        nav.addWidget(QLabel("Page Size:"))
        nav.addWidget(self.page_size_spin)
        layout.addLayout(nav)

        self._apply_layout()

    def load_contacts(self):
        self.page = 0
        self._apply_filters()

    def set_search_text(self, text: str):
        self.search_text = text
        self.page = 0
        self._apply_filters()


    def _apply_filters(self):
        sort_by = ""
        if self.sort_column is not None:
            sort_by = self.HEADERS[self.sort_column]
        sort_order = "desc" if self.sort_order == Qt.DescendingOrder else "asc"
        filters = {k: list(v) for k, v in self.filters.items()}
        contacts = self.db.fetch_contacts(
            filters=filters,
            search=self.search_text,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=self.page_size + 1,
            offset=self.page * self.page_size,
        )
        self._has_next = len(contacts) > self.page_size
        self.contacts = contacts[: self.page_size]
        self._show_contacts(self.contacts)
        self.prev_btn.setEnabled(self.page > 0)
        self.next_btn.setEnabled(self._has_next)
        self.page_label.setText(f"Page {self.page + 1}")

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
                    combo.currentIndexChanged[str].connect(
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
                    combo.currentIndexChanged[str].connect(
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
        self._status_callback("Disposition updated")

    def _on_status_changed(self, contact_id, status):
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"status": status})
        self._apply_filters()
        self._status_callback("Status updated")

    def _get_all_tags(self):
        tags = set(self.session_tags)
        tags.update(self.db.get_distinct_values("tags"))
        return sorted(tags)

    def _batch_add_tag(self):
        dialog = TagSelectionDialog(self._get_all_tags(), title="Add Tag to All Visible Contacts", allow_new=True, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        tag = dialog.selected_tag()
        if not tag:
            return
        self.session_tags.add(tag)
        for contact in self.filtered_contacts:
            self.db.add_tag(contact.get("profile_id"), tag)
        self._apply_filters()
        self._status_callback("Tag added")

    def _batch_remove_tag(self):
        dialog = TagSelectionDialog(self._get_all_tags(), title="Remove Tag from All Visible Contacts", allow_new=False, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        tag = dialog.selected_tag()
        if not tag:
            return
        for contact in self.filtered_contacts:
            self.db.remove_tag(contact.get("profile_id"), tag)
        self._apply_filters()
        self._status_callback("Tag removed")

    def start_quick_tag_mode(self):
        dialog = TagSelectionDialog(self._get_all_tags(), title="Select Tag", allow_new=True, parent=self)
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
            self.table.resizeColumnsToContents()
            self._status_callback("Column visibility updated")
            self.save_layout()

    def _open_filter_popup(self, logical):
        header = self.table.horizontalHeader()
        if logical < 0:
            return
        field = self.HEADERS[logical]
        values = self.db.get_distinct_values(field)
        popup = FilterPopup(values, field, self._run_ai_power_up, self)
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
        self._filter_header.set_active_section(logical)
        popup.show()

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
        self.page = 0
        self._apply_filters()
        self.save_layout()

    def _on_sort_requested(self, column, order, popup):
        self.sort_column = column
        self.sort_order = order
        popup.hide()
        self.page = 0
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
            self.table.verticalScrollBar().setValue(scroll)
            self._status_callback("Tag added")

    def _on_tag_button_clicked(self, row, contact_id, tag):
        if self.quick_mode != "remove":
            return
        scroll = self.table.verticalScrollBar().value()
        self.db.remove_tag(contact_id, tag)
        self._apply_filters()
        self.table.verticalScrollBar().setValue(scroll)
        self._status_callback("Tag removed")

    def _change_page(self, delta: int):
        new_page = self.page + delta
        if new_page < 0:
            return
        if delta > 0 and not self._has_next:
            return
        self.page = new_page
        self._apply_filters()

    def _on_page_size_changed(self):
        size = self.page_size_spin.value()
        if size <= 0:
            return
        self.page_size = size
        update_setting("page_size", size)
        self.page = 0
        self._apply_filters()

    def _load_layout(self):
        settings = get_settings().get("table_layout", {})
        visibility = settings.get("visibility", {})
        self.column_visibility.update(
            {k: v for k, v in visibility.items() if k in self.HEADERS}
        )
        order = [c for c in settings.get("order", self.HEADERS[:]) if c in self.HEADERS]
        if set(order) == set(self.HEADERS):
            self.column_order = order
        else:
            self.column_order = self.HEADERS[:]
        widths = settings.get("widths", {})
        self.column_widths = {
            k: w for k, w in widths.items() if k in self.HEADERS and isinstance(w, int) and w > 0
        }
        raw_filters = get_settings().get("table_filters", {})
        self.filters = {
            k: set(v) if not isinstance(v, set) else v
            for k, v in raw_filters.items()
            if v
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
            width = getattr(self, "column_widths", {}).get(name)
            if isinstance(width, int) and width > 0:
                header.resizeSection(idx, width)
            else:
                header.resizeSection(idx, header.sectionSizeHint(idx))
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
        settings["table_filters"] = {k: v for k, v in self.filters.items() if v}
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

    def _run_ai_power_up(self, field):
        """Run the configured AI prompt for the given column."""
        dialog = PowerUpDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        opts = dialog.options()

        if opts["scope"] == "limit":
            limit = opts["limit"]
            contacts = self.db.fetch_contacts(
                filters={k: list(v) for k, v in self.filters.items()},
                search=self.search_text,
                sort_by=self.HEADERS[self.sort_column] if self.sort_column is not None else "",
                sort_order="desc" if self.sort_order == Qt.DescendingOrder else "asc",
                limit=limit,
            )
        elif opts["scope"] == "view":
            contacts = self.db.fetch_contacts(
                filters={k: list(v) for k, v in self.filters.items()},
                search=self.search_text,
                sort_by=self.HEADERS[self.sort_column] if self.sort_column is not None else "",
                sort_order="desc" if self.sort_order == Qt.DescendingOrder else "asc",
            )
        else:
            contacts = self.db.fetch_contacts()

        mapping = {
            "target_company": "target_company_validation",
            "contact_icp_status": "icp_validation",
            "clients_of_contact": "clients_of_contact",
            "area_of_business": "area_of_business",
            "most_relevant_summit": "most_relevant_summit",
            "client_icp": "client_icp",
            "company_alias": "company_alias",
        }

        progress = QProgressDialog("Running AI Power Up...", None, 0, len(contacts), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)

        for step, contact in enumerate(contacts, start=1):
            if not opts["override"] and contact.get(field):
                progress.setValue(step)
                QApplication.processEvents()
                continue
            try:
                if field == "time_zone_utc":
                    offset = lookup_utc_offset(
                        contact.get("country", ""),
                        contact.get("state", ""),
                        contact.get("city", ""),
                    )
                    morning, afternoon = _calculate_call_times(offset)
                    self.db.update_contact(
                        contact["profile_id"],
                        {
                            "time_zone_utc": offset,
                            "morning_call_time": morning,
                            "afternoon_call_time": afternoon,
                        },
                    )
                else:
                    prompt = mapping.get(field)
                    if prompt:
                        result = run_prompt(prompt, contact)
                        self.db.update_contact(contact["profile_id"], {field: result})
            except Exception as exc:  # noqa: BLE001
                self._status_callback(str(exc))
            progress.setValue(step)
            QApplication.processEvents()

        progress.close()
        self.load_contacts()
        self._status_callback("AI Power Up completed")




