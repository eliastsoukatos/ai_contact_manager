from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt5.QtCore import Qt


class TagSelectionDialog(QDialog):
    """Dialog for selecting or entering a tag."""

    def __init__(self, tags, title="Select Tag", allow_new=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._allow_new = allow_new
        self._selected = ""
        layout = QVBoxLayout(self)
        if allow_new:
            self.input = QLineEdit()
            self.input.setPlaceholderText("New tag...")
            layout.addWidget(self.input)
        else:
            self.input = None
        self.list_widget = QListWidget()
        for tag in sorted(tags):
            item = QListWidgetItem(tag)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.list_widget.addItem(item)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_item_clicked(self, item):
        if self.input is not None:
            self.input.setText(item.text())
        self._selected = item.text()

    def selected_tag(self):
        if self.input is not None:
            text = self.input.text().strip()
            if text:
                return text
        return self._selected.strip()


class ModeIndicator(QWidget):
    """Small widget indicating an active quick mode."""

    def __init__(self, exit_callback, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(exit_callback)
        layout.addWidget(self.label)
        layout.addWidget(self.exit_btn)
        layout.addStretch(1)


