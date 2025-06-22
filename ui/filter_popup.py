from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QHBoxLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal


class FilterPopup(QWidget):
    """Popup widget for filtering and sorting column values."""

    selection_changed = pyqtSignal()
    sort_requested = pyqtSignal(Qt.SortOrder)
    closed = pyqtSignal()

    def __init__(self, values, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setWindowFlags(Qt.Popup)
        self.setFocusPolicy(Qt.StrongFocus)
        self._all_values = sorted({str(v) for v in values})
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search...")
        self.search_edit.textChanged.connect(self._populate)
        layout.addWidget(self.search_edit)

        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(lambda _i: self.selection_changed.emit())
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.clear_all_btn = QPushButton("Clear All")
        self.select_all_btn.clicked.connect(self.select_all)
        self.clear_all_btn.clicked.connect(self.clear_all)
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.clear_all_btn)
        layout.addLayout(btn_row)

        sort_row = QHBoxLayout()
        self.sort_asc = QPushButton("A-Z")
        self.sort_desc = QPushButton("Z-A")
        self.sort_asc.clicked.connect(lambda: self.sort_requested.emit(Qt.AscendingOrder))
        self.sort_desc.clicked.connect(lambda: self.sort_requested.emit(Qt.DescendingOrder))
        sort_row.addWidget(self.sort_asc)
        sort_row.addWidget(self.sort_desc)
        layout.addLayout(sort_row)

    def _populate(self):
        text = self.search_edit.text().lower()
        self.list_widget.clear()
        for val in self._all_values:
            if text and text not in val.lower():
                continue
            item = QListWidgetItem(val or "(Blank)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list_widget.addItem(item)
        self.selection_changed.emit()

    def selected_values(self):
        return {
            self.list_widget.item(i).text() if self.list_widget.item(i).text() != "(Blank)" else ""
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.Checked
        }

    def set_selected(self, selected):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked if item.text() in selected or (item.text() == "(Blank)" and "" in selected) else Qt.Unchecked)

    def select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)
        self.selection_changed.emit()

    def clear_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)
        self.selection_changed.emit()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def hideEvent(self, event):
        self.closed.emit()
        super().hideEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
