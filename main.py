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
from ai.enrichment import enrich_database, estimate_steps


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VibeList")
        self.db = DBManager()
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #FFE5B4;")
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

        enrich_action = QAction(
            self.style().standardIcon(QStyle.SP_MediaPlay),
            "Run AI Enrichment",
            self,
        )
        enrich_action.triggered.connect(self._run_ai_enrichment)
        menu.addAction(enrich_action)

        columns_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogContentsView),
            "Customize Columns",
            self,
        )
        columns_action.triggered.connect(self.table_widget._customize_columns)
        menu.addAction(columns_action)

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

        self.table_widget = ContactsTableWidget(self.db, self.show_status_message)
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

    def _run_ai_enrichment(self):
        total = estimate_steps(self.db)
        if total == 0:
            self.show_status_message("No enrichment needed")
            return
        progress = QProgressDialog("Running AI enrichment...", None, 0, total, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        self.table_widget.setDisabled(True)
        self.search_bar.setDisabled(True)

        def _progress(step, tot):
            progress.setMaximum(tot)
            progress.setValue(step)
            QApplication.processEvents()

        try:
            enrich_database(self.db, progress_callback=_progress, status_callback=self.show_status_message)
        except Exception as exc:  # noqa: BLE001
            self.show_status_message(str(exc), 5000)
        finally:
            progress.close()
            self.table_widget.setDisabled(False)
            self.search_bar.setDisabled(False)
            self.table_widget.load_contacts()

    def closeEvent(self, event):
        self.table_widget.save_layout()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
