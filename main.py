import sys
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
)
from PyQt5.QtCore import Qt

from db_manager import DBManager
from csv_importer import CSVImporter


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

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contacts...")
        self.search_bar.textChanged.connect(self._filter_contacts)
        layout.addWidget(self.search_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
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
            ]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def _load_contacts(self):
        """Fetch contacts from the database and display them."""
        self.contacts = self.db.fetch_contacts()
        self._show_contacts(self.contacts)

    def _filter_contacts(self, text):
        """Filter displayed contacts based on the search text."""
        text = text.lower()
        filtered = [
            c
            for c in self.contacts
            if any(
                text in (c.get(field, "") or "").lower()
                for field in ("first_name", "last_name", "email", "company_name")
            )
        ]
        self._show_contacts(filtered)

    def _show_contacts(self, contacts):
        """Populate the table with the given contacts."""
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
            tags_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 9, tags_item)

            state_item = QTableWidgetItem(str(contact.get("state", "")))
            state_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 10, state_item)
        self.table.resizeColumnsToContents()

    def _on_disposition_changed(self, contact_id, disposition):
        """Update disposition in the database and refresh the table."""
        if not contact_id:
            return
        self.db.update_contact(contact_id, {"contact_disposition": disposition})
        self.contacts = self.db.fetch_contacts()
        self._filter_contacts(self.search_bar.text())

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
