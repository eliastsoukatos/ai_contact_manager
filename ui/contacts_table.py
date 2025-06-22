from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QInputDialog,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt

from db_manager import DBManager


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
        "job_title",
        "personal_linkedin_url",
        "contact_disposition",
        "tags",
        "state",
        "status",
    ]

    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.contacts = []
        self.filtered_contacts = []
        self.search_text = ""
        self.column_visibility = {h: True for h in self.HEADERS}
        self._setup_ui()
        self.load_contacts()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.add_tag_button = QPushButton("Add Tag to All Visible")
        self.add_tag_button.clicked.connect(self._batch_add_tag)
        layout.addWidget(self.add_tag_button)

        self.remove_tag_button = QPushButton("Remove Tag from All Visible")
        self.remove_tag_button.clicked.connect(self._batch_remove_tag)
        layout.addWidget(self.remove_tag_button)

        self.status_all_button = QPushButton("Set Status for All Visible")
        self.status_all_button.clicked.connect(self._batch_set_status)
        layout.addWidget(self.status_all_button)

        self.column_settings_button = QPushButton("Customize Columns")
        self.column_settings_button.clicked.connect(self._customize_columns)
        layout.addWidget(self.column_settings_button)

        self.tag_filter = CheckableComboBox()
        self.tag_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.tag_filter)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

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

        filtered = []
        for c in self.contacts:
            if text and not any(
                text in (c.get(f, "") or "").lower()
                for f in ("first_name", "last_name", "email", "company_name")
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
                else:
                    value = str(contact.get(header, ""))
                    item = QTableWidgetItem(value)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.table.setItem(row, col, item)

            self.table.setColumnHidden(col, not self.column_visibility[header])
        for idx, header in enumerate(self.HEADERS):
            self.table.setColumnHidden(idx, not self.column_visibility[header])
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()

    def _on_item_changed(self, item):
        if self.HEADERS[item.column()] != "tags":
            return
        contact_id = item.data(Qt.UserRole)
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"tags": item.text()})
        self.contacts = self.db.fetch_contacts()
        self._refresh_tag_filter()
        self._apply_filters()

    def _on_disposition_changed(self, contact_id, disposition):
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"contact_disposition": disposition})
        self.contacts = self.db.fetch_contacts()
        self._apply_filters()

    def _on_status_changed(self, contact_id, status):
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"status": status})
        self.contacts = self.db.fetch_contacts()
        self._apply_filters()

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




