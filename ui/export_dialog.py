from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedLayout,
    QGridLayout,
)
from typing import List, Tuple


class ExportOptionsDialog(QDialog):
    """Dialog to configure export options."""

    def __init__(self, headers: List[str], selected: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export View")
        self._headers = headers
        self._selected = set(selected)

        self._stack = QStackedLayout(self)
        self._build_main_page()
        self._build_fields_page()
        self._stack.setCurrentIndex(0)

    def _build_main_page(self):
        page = QWidget()
        form = QFormLayout(page)

        self.folder_edit = QLineEdit()
        form.addRow("Folder Name", self.folder_edit)

        self.tz_split = QCheckBox("Split by time zone")
        form.addRow(self.tz_split)

        self.export_all = QCheckBox("Export all filtered contacts")
        form.addRow(self.export_all)

        self.group_spin = QSpinBox()
        self.group_spin.setRange(1, 99)
        self.group_spin.setValue(1)
        form.addRow("Number of groups", self.group_spin)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(0, 100000)
        self.chunk_spin.setValue(0)
        form.addRow("Contacts per file", self.chunk_spin)

        field_btn = QPushButton("Select Fields")
        field_btn.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        form.addRow(field_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

        self._stack.addWidget(page)

    def _build_fields_page(self):
        page = QWidget()
        cols = 4
        layout = QGridLayout(page)
        self.field_checks = {}
        for idx, header in enumerate(self._headers):
            cb = QCheckBox(header)
            if header == "mobile":
                cb.setChecked(True)
                cb.setEnabled(False)
            else:
                cb.setChecked(header in self._selected)
            row = idx // cols
            col = idx % cols
            layout.addWidget(cb, row, col)
            self.field_checks[header] = cb

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        layout.addWidget(
            back_btn,
            (len(self._headers) + cols - 1) // cols + 1,
            0,
            1,
            cols,
        )
        self._stack.addWidget(page)

    def options(self) -> Tuple[str, bool, int, int, List[str], bool]:
        fields = [
            h for h, cb in self.field_checks.items() if cb.isChecked()
        ]
        return (
            self.folder_edit.text().strip(),
            self.tz_split.isChecked(),
            self.group_spin.value(),
            self.chunk_spin.value(),
            fields,
            self.export_all.isChecked(),
        )
