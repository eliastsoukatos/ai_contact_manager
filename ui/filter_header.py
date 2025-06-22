from PyQt5.QtWidgets import QHeaderView, QToolButton
from PyQt5.QtCore import Qt, pyqtSignal


class FilterHeader(QHeaderView):
    """Horizontal header showing filter arrows on hover or when active."""

    filter_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setMouseTracking(True)
        self._hover_section = None
        self._active_section = None
        self._button = QToolButton(self)
        self._button.setText("\u25BC")  # down arrow
        self._button.setFixedSize(16, 16)
        self._button.hide()
        self._button.clicked.connect(self._button_clicked)
        self.sectionResized.connect(lambda *_: self._update_button())
        self.sectionMoved.connect(lambda *_: self._update_button())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        index = self.logicalIndexAt(event.pos())
        if index != self._hover_section:
            self._hover_section = index
            self._update_button()

    def _button_clicked(self):
        if self._hover_section is not None:
            self._active_section = self._hover_section
            self.filter_requested.emit(self._hover_section)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        index = self.logicalIndexAt(event.pos())
        if index != self._hover_section:
            self._hover_section = index
            self._update_button()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover_section = None
        if self._active_section is None:
            self._button.hide()

    def _update_button(self):
        section = self._active_section if self._active_section is not None else self._hover_section
        if section is None:
            self._button.hide()
            return
        rect = self.sectionRect(section)
        x = rect.right() - self._button.width() - 2
        y = rect.center().y() - self._button.height() // 2
        self._button.move(x, y)
        self._button.show()

    def set_active_section(self, index):
        self._active_section = index
        self._update_button()
        if index is None and self._hover_section is None:
            self._button.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_button()
