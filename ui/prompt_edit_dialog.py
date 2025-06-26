from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QPlainTextEdit,
    QDialogButtonBox,
    QLabel,
    QHBoxLayout,
    QWidget,
)
import re

from config.settings import get_settings, update_setting


class PromptEditDialog(QDialog):
    """Dialog for editing an AI prompt template."""

    def __init__(self, prompt_key: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Prompt")
        self._key = prompt_key
        layout = QVBoxLayout(self)
        prompts = get_settings().get("prompts", {})
        self.edit = QPlainTextEdit(prompts.get(prompt_key, ""))
        self.edit.setMinimumWidth(500)
        self.edit.setMinimumHeight(300)
        layout.addWidget(self.edit)
        self.vars_container = QWidget()
        self.vars_layout = QHBoxLayout(self.vars_container)
        self.vars_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.vars_container)
        self.edit.textChanged.connect(self._update_vars)
        self._update_vars()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        update_setting(f"prompts.{self._key}", self.edit.toPlainText())
        super().accept()

    def _update_vars(self):
        """Parse the prompt and display detected dynamic variables."""
        text = self.edit.toPlainText()
        vars_found = sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", text)))
        while self.vars_layout.count():
            item = self.vars_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for var in vars_found:
            label = QLabel(var)
            label.setStyleSheet(
                "QLabel { border: 1px solid #888; border-radius: 4px; padding: 2px 4px; }"
            )
            self.vars_layout.addWidget(label)
        self.vars_container.setVisible(bool(vars_found))
