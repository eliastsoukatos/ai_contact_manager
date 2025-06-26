from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QSpinBox,
    QGroupBox,
    QCheckBox,
)


class PowerUpDialog(QDialog):
    """Dialog to configure AI Power Up options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Power Up")
        layout = QVBoxLayout(self)

        scope_box = QGroupBox("Run for")
        scope_layout = QVBoxLayout(scope_box)
        self.limit_radio = QRadioButton("Specific number of contacts")
        limit_row = QHBoxLayout()
        limit_row.addWidget(self.limit_radio)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 10000)
        self.limit_spin.setValue(10)
        limit_row.addWidget(self.limit_spin)
        scope_layout.addLayout(limit_row)
        self.view_radio = QRadioButton("All contacts in this view")
        scope_layout.addWidget(self.view_radio)
        self.all_radio = QRadioButton("All contacts in database")
        self.all_radio.setChecked(True)
        scope_layout.addWidget(self.all_radio)
        layout.addWidget(scope_box)

        override_box = QGroupBox("Update mode")
        override_layout = QVBoxLayout(override_box)
        self.override_radio = QRadioButton("Override existing values")
        self.empty_radio = QRadioButton("Only fill empty values")
        self.empty_radio.setChecked(True)
        override_layout.addWidget(self.override_radio)
        override_layout.addWidget(self.empty_radio)
        layout.addWidget(override_box)

        self.search_checkbox = QCheckBox("Internet Search")
        layout.addWidget(self.search_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def options(self):
        if self.limit_radio.isChecked():
            scope = "limit"
        elif self.view_radio.isChecked():
            scope = "view"
        else:
            scope = "all"
        return {
            "scope": scope,
            "limit": self.limit_spin.value(),
            "override": self.override_radio.isChecked(),
            "web_search": self.search_checkbox.isChecked(),
        }
