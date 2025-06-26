import sys
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QAction,
    QStyle,
    QProgressDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QStatusBar,
    QMenu,
    QToolButton,
)
from PyQt5.QtCore import Qt, QSize

from db_manager import DBManager
from csv_importer import CSVImporter
from ui.contacts_table import ContactsTableWidget
from ui.settings_panel import SettingsDialog



class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VibeList")
        self.db = DBManager()
        self._setup_ui()

    def _setup_ui(self):
        # Instantiate main table widget first so actions can reference it
        self.table_widget = ContactsTableWidget(self.db, self.show_status_message)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Header with hamburger menu and search bar
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self.menu_button = QToolButton()
        self.menu_button.setText("\u2630")  # hamburger icon
        self.menu_button.setStyleSheet("font-size: 18px;")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)

        # Actions
        import_action = QAction(
            self.style().standardIcon(QStyle.SP_DirOpenIcon),
            "Import Contacts from CSV",
            self,
        )
        import_action.triggered.connect(self._import_csv)
        menu.addAction(import_action)

        export_action = QAction(
            self.style().standardIcon(QStyle.SP_DialogSaveButton),
            "Export View",
            self,
        )
        export_action.triggered.connect(self.table_widget.export_view)
        menu.addAction(export_action)

        add_tag_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogNewFolder),
            "Add Tag to All Visible Contacts",
            self,
        )
        add_tag_action.triggered.connect(self.table_widget._batch_add_tag)
        menu.addAction(add_tag_action)

        quick_tag_action = QAction(
            self.style().standardIcon(QStyle.SP_DialogYesButton),
            "Quick Tag Contacts",
            self,
        )
        quick_tag_action.triggered.connect(self.table_widget.start_quick_tag_mode)
        menu.addAction(quick_tag_action)

        remove_tag_action = QAction(
            self.style().standardIcon(QStyle.SP_TrashIcon),
            "Remove Tag",
            self,
        )
        remove_tag_action.triggered.connect(self.table_widget._batch_remove_tag)
        menu.addAction(remove_tag_action)

        quick_remove_action = QAction(
            self.style().standardIcon(QStyle.SP_DialogNoButton),
            "Remove Tag Mode",
            self,
        )
        quick_remove_action.triggered.connect(self.table_widget.start_quick_remove_mode)
        menu.addAction(quick_remove_action)

        status_action = QAction(
            self.style().standardIcon(QStyle.SP_DialogApplyButton),
            "Set Status for Visible Contacts",
            self,
        )
        status_action.triggered.connect(self.table_widget._batch_set_status)
        menu.addAction(status_action)


        columns_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogContentsView),
            "Customize Columns",
            self,
        )
        columns_action.triggered.connect(self.table_widget._customize_columns)
        menu.addAction(columns_action)

        add_col_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogNewFolder),
            "Add Column",
            self,
        )
        add_col_action.triggered.connect(self.table_widget.add_custom_column)
        menu.addAction(add_col_action)

        del_col_action = QAction(
            self.style().standardIcon(QStyle.SP_TrashIcon),
            "Delete Column",
            self,
        )
        del_col_action.triggered.connect(self.table_widget.delete_custom_column)
        menu.addAction(del_col_action)

        settings_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView),
            "Settings",
            self,
        )
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        self.menu_button.setMenu(menu)
        header_row.addWidget(self.menu_button)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search contacts...")
        self.search_bar.setFixedHeight(24)
        header_row.addWidget(self.search_bar, 1)
        main_layout.addLayout(header_row)

        # Main table view
        main_layout.addWidget(self.table_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.search_bar.textChanged.connect(self.table_widget.set_search_text)

    def show_status_message(self, text, timeout=3000):
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(text, timeout)

    def _open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

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
        self.show_status_message("Import completed")


    def closeEvent(self, event):
        self.table_widget.save_layout()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
