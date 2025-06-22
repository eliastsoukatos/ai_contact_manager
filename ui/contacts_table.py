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
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt

from db_manager import DBManager
from config.settings import get_settings, save_settings


class CheckableComboBox(QComboBox):
    """Combo box allowing multiple selections via checkboxes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModel(QStandardItemModel(self))
        self.view().pressed.connect(self._handle_pressed)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Filter by tag...")

    def _handle_pressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        self._update_text()
        self.currentIndexChanged.emit(-1)

    def checked_items(self):
        return [
            self.model().item(i).text()
            for i in range(self.model().rowCount())
            if self.model().item(i).checkState() == Qt.Checked
        ]

    def _update_text(self):
        self.blockSignals(True)
        self.lineEdit().setText(", ".join(self.checked_items()))
        self.blockSignals(False)


class ContactsTableWidget(QWidget):
    """Widget displaying contacts with filtering and batch actions."""

    HEADERS = [
        "mobile",
        "first_name",
        "last_name",
        "email",
        "company_name",
        "website",
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
        "state",
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
        self._load_layout()
        self._setup_ui()
        self.load_contacts()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Tag filter dropdown is created here but not added to the internal
        # layout so the main window can position it next to the search bar.
        self.tag_filter = CheckableComboBox()
        self.tag_filter.currentIndexChanged.connect(self._apply_filters)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellDoubleClicked.connect(self._handle_cell_double_clicked)
        layout.addWidget(self.table)

        self._apply_layout()

    def load_contacts(self):
        self.contacts = self.db.fetch_contacts()
        self._refresh_tag_filter()
        self._apply_filters()

    def set_search_text(self, text: str):
        self.search_text = text
        self._apply_filters()

    def _refresh_tag_filter(self):
        tags = set()
        for c in self.contacts:
            if c.get("tags"):
                tags.update(t.strip() for t in c["tags"].split(",") if t.strip())
        model = self.tag_filter.model()
        model.clear()
        for tag in sorted(tags):
            item = QStandardItem(tag)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setData(Qt.Unchecked, Qt.CheckStateRole)
            model.appendRow(item)
        self.tag_filter._update_text()

    def _apply_filters(self):
        text = self.search_text.lower()
        selected_tags = self.tag_filter.checked_items()

        visible_fields = [
            h for h in self.HEADERS if self.column_visibility.get(h, True)
        ]

        filtered = []
        for c in self.contacts:
            if text and not any(
                text in str(c.get(f, "")).lower() for f in visible_fields
            ):
                continue
            if selected_tags:
                contact_tags = [
                    t.strip()
                    for t in (c.get("tags", "") or "").split(",")
                    if t.strip()
                ]
                if not any(tag in contact_tags for tag in selected_tags):
                    continue
            filtered.append(c)

        self._show_contacts(filtered)

    def _show_contacts(self, contacts):
        self.filtered_contacts = contacts
        self.table.blockSignals(True)
        self.table.setRowCount(len(contacts))
        for row, contact in enumerate(contacts):
            for col, header in enumerate(self.HEADERS):
                if header == "contact_disposition":
                    combo = QComboBox()
                    dispositions = [
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
                    combo.setCurrentText(contact.get("contact_disposition", ""))
                    combo.currentTextChanged.connect(
                        lambda value, cid=contact.get("profile_id"): self._on_disposition_changed(cid, value)
                    )
                    self.table.setCellWidget(row, col, combo)
                elif header == "tags":
                    tags_item = QTableWidgetItem(str(contact.get("tags", "")))
                    tags_item.setFlags(
                        Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
                    )
                    tags_item.setData(Qt.UserRole, contact.get("profile_id"))
                    self.table.setItem(row, col, tags_item)
                elif header == "status":
                    combo = QComboBox()
                    combo.addItems(["active", "inactive"])
                    combo.setCurrentText(contact.get("status", ""))
                    combo.currentTextChanged.connect(
                        lambda value, cid=contact.get("profile_id"): self._on_status_changed(cid, value)
                    )
                    self.table.setCellWidget(row, col, combo)
                elif header in ["email", "personal_linkedin_url"]:
                    value = str(contact.get(header, ""))
                    if value:
                        if header == "email":
                            href = f"mailto:{value}"
                        else:
                            href = value
                        label = QLabel(f"<a href='{href}'>{value}</a>")
                        label.setOpenExternalLinks(True)
                        label.setProperty("raw", value)
                        label.linkActivated.connect(
                            lambda _url, v=value: self._status_callback(f"Opened {v}")
                        )
                        self.table.setCellWidget(row, col, label)
                    else:
                        self.table.setItem(row, col, QTableWidgetItem(""))
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
            "time_zone_utc",
        }
        if header not in editable:
            return
        contact_id = item.data(Qt.UserRole)
        if not contact_id:
            return
        self.db.update_contact(contact_id, {header: item.text()})
        self.contacts = self.db.fetch_contacts()
        if header == "tags":
            self._refresh_tag_filter()
        self._apply_filters()
        self._status_callback(f"{header.replace('_', ' ').title()} updated")

    def _on_disposition_changed(self, contact_id, disposition):
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"contact_disposition": disposition})
        self.contacts = self.db.fetch_contacts()
        self._apply_filters()
        self._status_callback("Disposition updated")

    def _on_status_changed(self, contact_id, status):
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"status": status})
        self.contacts = self.db.fetch_contacts()
        self._apply_filters()
        self._status_callback("Status updated")

    def _batch_add_tag(self):
        tag, ok = QInputDialog.getText(self, "Add Tag", "Tag:")
        if not ok or not tag.strip():
            return
        tag = tag.strip()
        for contact in self.filtered_contacts:
            tags = [t for t in (contact.get("tags", "") or "").split(",") if t]
            if tag not in tags:
                tags.append(tag)
                self.db.update_contact(
                    contact.get("profile_id"), {"tags": ",".join(tags)}
                )
        self.contacts = self.db.fetch_contacts()
        self._refresh_tag_filter()
        self._apply_filters()
        self._status_callback("Tag added")

    def _batch_remove_tag(self):
        tag, ok = QInputDialog.getText(self, "Remove Tag", "Tag to remove:")
        if not ok or not tag.strip():
            return
        tag = tag.strip()
        for contact in self.filtered_contacts:
            tags = [t for t in (contact.get("tags", "") or "").split(",") if t]
            if tag in tags:
                tags = [t for t in tags if t != tag]
                self.db.update_contact(
                    contact.get("profile_id"), {"tags": ",".join(tags)}
                )
        self.contacts = self.db.fetch_contacts()
        self._refresh_tag_filter()
        self._apply_filters()
        self._status_callback("Tag removed")

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
        self.contacts = self.db.fetch_contacts()
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
            self._status_callback("Column visibility updated")
            self.save_layout()

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

    def _load_layout(self):
        settings = get_settings().get("table_layout", {})
        self.column_visibility.update(settings.get("visibility", {}))
        self.column_order = settings.get("order", self.HEADERS[:])
        self.column_widths = settings.get("widths", {})

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
        save_settings()




