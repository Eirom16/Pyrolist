from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QFont


class ClickableLabel(QLabel):
    clicked = Qt.UserType

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._callback = None

    def set_clicked_callback(self, callback):
        self._callback = callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._callback:
            self._callback()
        super().mousePressEvent(event)