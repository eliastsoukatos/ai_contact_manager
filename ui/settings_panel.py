from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)
from PyQt5.QtCore import Qt, QTime
from typing import Optional

from config.settings import get_settings, update_setting


class SettingsDialog(QDialog):
    """Dialog for editing application and AI settings."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._settings = get_settings()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        # API Keys
        self.api_key_edit = QLineEdit(self._settings.get("openai_api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-...")
        self.api_key_edit.setToolTip("Your OpenAI API key")
        self.api_key_edit.editingFinished.connect(
            lambda: update_setting("openai_api_key", self.api_key_edit.text())
        )
        form.addRow("OpenAI API Key", self.api_key_edit)

        self.groq_key_edit = QLineEdit(self._settings.get("groq_api_key", ""))
        self.groq_key_edit.setEchoMode(QLineEdit.Password)
        self.groq_key_edit.setPlaceholderText("gsk-...")
        self.groq_key_edit.setToolTip("Your Groq API key")
        self.groq_key_edit.editingFinished.connect(
            lambda: update_setting("groq_api_key", self.groq_key_edit.text())
        )
        form.addRow("Groq API Key", self.groq_key_edit)

        self.pplx_key_edit = QLineEdit(self._settings.get("perplexity_api_key", ""))
        self.pplx_key_edit.setEchoMode(QLineEdit.Password)
        self.pplx_key_edit.setPlaceholderText("pk-...")
        self.pplx_key_edit.setToolTip("Your Perplexity API key")
        self.pplx_key_edit.editingFinished.connect(
            lambda: update_setting("perplexity_api_key", self.pplx_key_edit.text())
        )
        form.addRow("Perplexity API Key", self.pplx_key_edit)

        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.addItems(
            [
                "gpt-4.1",
                "gpt-4.1-mini",
                "gpt-4.1-nano",
                "gpt-4o-mini",
                "o3-mini",
                "gemma2-9b-it",
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "meta-llama/llama-guard-4-12b",
                "sonar",
                "sonar-pro",
            ]
        )
        self.model_combo.setCurrentText(self._settings.get("llm_model", "gpt-4.1"))
        self.model_combo.currentIndexChanged[str].connect(
            lambda text: update_setting("llm_model", text)
        )
        form.addRow("LLM Model", self.model_combo)

        layout.addLayout(form)

        script_box = QGroupBox("Script Template")
        script_layout = QVBoxLayout(script_box)
        self.script_edit = QPlainTextEdit(self._settings.get("script_template", ""))
        self.script_edit.setMinimumHeight(150)
        self.script_edit.textChanged.connect(
            lambda: update_setting("script_template", self.script_edit.toPlainText())
        )
        script_layout.addWidget(self.script_edit)
        layout.addWidget(script_box)



        # Time zone settings
        tz_box = QGroupBox("Time Zone")
        tz_layout = QFormLayout(tz_box)
        tz_settings = self._settings.get("timezone", {})

        self.utc_offset_spin = QSpinBox()
        self.utc_offset_spin.setRange(-12, 14)
        self.utc_offset_spin.setValue(int(tz_settings.get("utc_offset", 0)))
        self.utc_offset_spin.setToolTip("Default UTC offset")
        self.utc_offset_spin.valueChanged.connect(
            lambda val: update_setting("timezone.utc_offset", val)
        )
        tz_layout.addRow("UTC Offset", self.utc_offset_spin)

        self.morning_time = QTimeEdit()
        self.morning_time.setDisplayFormat("HH:mm")
        self.morning_time.setTime(
            QTime.fromString(tz_settings.get("morning_call", "09:00"), "HH:mm")
        )
        self.morning_time.timeChanged.connect(
            lambda t: update_setting("timezone.morning_call", t.toString("HH:mm"))
        )
        tz_layout.addRow("Morning Call", self.morning_time)

        self.afternoon_time = QTimeEdit()
        self.afternoon_time.setDisplayFormat("HH:mm")
        self.afternoon_time.setTime(
            QTime.fromString(tz_settings.get("afternoon_call", "15:00"), "HH:mm")
        )
        self.afternoon_time.timeChanged.connect(
            lambda t: update_setting("timezone.afternoon_call", t.toString("HH:mm"))
        )
        tz_layout.addRow("Afternoon Call", self.afternoon_time)

        layout.addWidget(tz_box)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

