import sys
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QToolBar,
    QAction,
    QStyle,
    QProgressDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QStatusBar,
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

        self.table_widget = ContactsTableWidget(self.db, self.show_status_message)
        main_layout.addLayout(search_row)

        # Horizontal toolbar with compact actions
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))

        import_action = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "Import", self)
        import_action.setToolTip("Import contacts from CSV")
        import_action.triggered.connect(self._import_csv)
        toolbar.addAction(import_action)

        export_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Export View", self)
        export_action.setToolTip("Export visible contacts to CSV")
        export_action.triggered.connect(self.table_widget.export_view)
        toolbar.addAction(export_action)

        add_tag_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogNewFolder), "Add Tag to All", self)
        add_tag_action.setToolTip("Add tag to all visible contacts")
        add_tag_action.triggered.connect(self.table_widget._batch_add_tag)
        toolbar.addAction(add_tag_action)

        remove_tag_action = QAction(self.style().standardIcon(QStyle.SP_TrashIcon), "Remove Tag", self)
        remove_tag_action.setToolTip("Remove tag from all visible contacts")
        remove_tag_action.triggered.connect(self.table_widget._batch_remove_tag)
        toolbar.addAction(remove_tag_action)

        quick_tag_action = QAction(self.style().standardIcon(QStyle.SP_DialogYesButton), "Quick Tag", self)
        quick_tag_action.setToolTip("Tag contacts quickly")
        quick_tag_action.triggered.connect(self.table_widget.start_quick_tag_mode)
        toolbar.addAction(quick_tag_action)

        quick_remove_action = QAction(self.style().standardIcon(QStyle.SP_DialogNoButton), "Remove Tag Mode", self)
        quick_remove_action.setToolTip("Quickly remove tag from contacts")
        quick_remove_action.triggered.connect(self.table_widget.start_quick_remove_mode)
        toolbar.addAction(quick_remove_action)

        status_action = QAction(self.style().standardIcon(QStyle.SP_DialogApplyButton), "Set Status", self)
        status_action.setToolTip("Set status for all visible contacts")
        status_action.triggered.connect(self.table_widget._batch_set_status)
        toolbar.addAction(status_action)

        enrich_action = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Run AI", self)
        enrich_action.setToolTip("Run AI enrichment for visible contacts")
        enrich_action.triggered.connect(self._run_ai_enrichment)
        toolbar.addAction(enrich_action)

        columns_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogContentsView), "Columns", self)
        columns_action.setToolTip("Customize visible columns")
        columns_action.triggered.connect(self.table_widget._customize_columns)
        toolbar.addAction(columns_action)

        settings_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Settings", self)
        settings_action.setToolTip("Application and AI settings")
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        main_layout.addWidget(toolbar)

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
