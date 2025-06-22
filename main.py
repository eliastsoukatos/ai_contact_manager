import sys
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt

from db_manager import DBManager
from csv_importer import CSVImporter


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


class MainWindow(QMainWindow):
    """Main application window with a table view of contacts."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VibeList AI Contact Manager")

        self.db = DBManager()
        self.contacts = []

        self._setup_ui()
        self._load_contacts()

    def _setup_ui(self):
        """Create widgets and layouts."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.import_button = QPushButton("Import CSV")
        self.import_button.clicked.connect(self._import_csv)
        layout.addWidget(self.import_button)

        self.batch_tag_button = QPushButton("Add Tag to All Visible")
        self.batch_tag_button.clicked.connect(self._batch_add_tag)
        layout.addWidget(self.batch_tag_button)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contacts...")
        self.search_bar.textChanged.connect(self._apply_filters)
        layout.addWidget(self.search_bar)

        self.tag_filter = CheckableComboBox()
        self.tag_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.tag_filter)

        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels(
            [
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
        )
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

    def _load_contacts(self):
        """Fetch contacts from the database and display them."""
        self.contacts = self.db.fetch_contacts()
        self._refresh_tag_filter()
        self._show_contacts(self.contacts)

    def _refresh_tag_filter(self):
        """Populate tag filter with unique tags from all contacts."""
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
        """Filter contacts based on search text and selected tags."""
        text = self.search_bar.text().lower()
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
        """Populate the table with the given contacts."""
        self.filtered_contacts = contacts
        self.table.blockSignals(True)
        self.table.setRowCount(len(contacts))
        for row, contact in enumerate(contacts):
            values = [
                contact.get("mobile", ""),
                contact.get("first_name", ""),
                contact.get("last_name", ""),
                contact.get("email", ""),
                contact.get("company_name", ""),
                contact.get("website", ""),
                contact.get("job_title", ""),
                contact.get("personal_linkedin_url", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, col, item)

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
            self.table.setCellWidget(row, 8, combo)

            tags_item = QTableWidgetItem(str(contact.get("tags", "")))
            tags_item.setFlags(
                Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
            )
            tags_item.setData(Qt.UserRole, contact.get("profile_id"))
            self.table.setItem(row, 9, tags_item)

            state_item = QTableWidgetItem(str(contact.get("state", "")))
            state_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 10, state_item)

            status_item = QTableWidgetItem(str(contact.get("status", "")))
            status_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 11, status_item)
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()

    def _on_item_changed(self, item):
        """Handle inline edits for the tags column."""
        if item.column() != 9:
            return
        contact_id = item.data(Qt.UserRole)
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"tags": item.text()})
        self.contacts = self.db.fetch_contacts()
        self._refresh_tag_filter()
        self._apply_filters()

    def _batch_add_tag(self):
        """Add a tag to all currently visible contacts."""
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

    def _on_disposition_changed(self, contact_id, disposition):
        """Update disposition in the database and refresh the table."""
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"contact_disposition": disposition})
        self.contacts = self.db.fetch_contacts()
        self._apply_filters()

    def _import_csv(self):
        """Prompt the user for a CSV file and import its contents."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV file",
            "",
            "CSV files (*.csv);;All files (*)",
        )
        if not file_path:
            return

        CSVImporter(file_path, self.db).import_contacts()
        self._load_contacts()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
