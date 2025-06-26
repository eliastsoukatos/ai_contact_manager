from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QDialogButtonBox

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
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        update_setting(f"prompts.{self._key}", self.edit.toPlainText())
        super().accept()
