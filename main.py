import sys
from PyQt5.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt

from db_manager import DBManager


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

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contacts...")
        self.search_bar.textChanged.connect(self._filter_contacts)
        layout.addWidget(self.search_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "first_name",
                "last_name",
                "email",
                "company_name",
                "job_title",
                "state",
                "tags",
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
                contact.get("first_name", ""),
                contact.get("last_name", ""),
                contact.get("email", ""),
                contact.get("company_name", ""),
                contact.get("job_title", ""),
                contact.get("state", ""),
                contact.get("tags", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
