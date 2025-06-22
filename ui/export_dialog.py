from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
)
from typing import Tuple


class ExportOptionsDialog(QDialog):
    """Dialog to configure export options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export View")
        form = QFormLayout(self)

        self.folder_edit = QLineEdit()
        form.addRow("Folder Name", self.folder_edit)

        self.base_edit = QLineEdit()
        form.addRow("Base File Name", self.base_edit)

        self.tz_split = QCheckBox("Split by time zone")
        form.addRow(self.tz_split)

        self.group_spin = QSpinBox()
        self.group_spin.setRange(1, 99)
        self.group_spin.setValue(1)
        form.addRow("Number of groups", self.group_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

    def options(self) -> Tuple[str, str, bool, int]:
        return (
            self.folder_edit.text().strip(),
            self.base_edit.text().strip(),
            self.tz_split.isChecked(),
            self.group_spin.value(),
        )
