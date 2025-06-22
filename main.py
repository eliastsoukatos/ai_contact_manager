import sys
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QToolBar,
    QAction,
    QStyle,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt, QSize

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
        main_layout = QVBoxLayout(central)

        # Search bar and tag filter row
        search_row = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contacts...")
        search_row.addWidget(self.search_bar, 1)

        self.table_widget = ContactsTableWidget(self.db)
        search_row.addWidget(self.table_widget.tag_filter)
        main_layout.addLayout(search_row)

        # Horizontal toolbar with compact actions
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))

        import_action = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "Import", self)
        import_action.setToolTip("Import contacts from CSV")
        import_action.triggered.connect(self._import_csv)
        toolbar.addAction(import_action)

        add_tag_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogNewFolder), "Add Tag", self)
        add_tag_action.setToolTip("Add tag to all visible contacts")
        add_tag_action.triggered.connect(self.table_widget._batch_add_tag)
        toolbar.addAction(add_tag_action)

        remove_tag_action = QAction(self.style().standardIcon(QStyle.SP_TrashIcon), "Remove Tag", self)
        remove_tag_action.setToolTip("Remove tag from all visible contacts")
        remove_tag_action.triggered.connect(self.table_widget._batch_remove_tag)
        toolbar.addAction(remove_tag_action)

        status_action = QAction(self.style().standardIcon(QStyle.SP_DialogApplyButton), "Set Status", self)
        status_action.setToolTip("Set status for all visible contacts")
        status_action.triggered.connect(self.table_widget._batch_set_status)
        toolbar.addAction(status_action)

        columns_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogContentsView), "Columns", self)
        columns_action.setToolTip("Customize visible columns")
        columns_action.triggered.connect(self.table_widget._customize_columns)
        toolbar.addAction(columns_action)

        main_layout.addWidget(toolbar)

        main_layout.addWidget(self.table_widget)

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
