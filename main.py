import sys
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from db_manager import DBManager
from csv_importer import CSVImporter
from ui.contacts_table import ContactsTableWidget


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VibeList AI Contact Manager")
        self.db = DBManager()
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.import_button = QPushButton("Import CSV")
        self.import_button.clicked.connect(self._import_csv)
        layout.addWidget(self.import_button)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contacts...")
        layout.addWidget(self.search_bar)

        self.table_widget = ContactsTableWidget(self.db)
        layout.addWidget(self.table_widget)

        self.search_bar.textChanged.connect(self.table_widget.set_search_text)

    def _import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV file",
            "",
            "CSV files (*.csv);;All files (*)",
        )
        if not file_path:
            return
        CSVImporter(file_path, self.db).import_contacts()
        self.table_widget.load_contacts()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
