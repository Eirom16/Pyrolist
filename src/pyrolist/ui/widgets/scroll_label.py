from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QTimer, Qt


class ScrollLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scroll)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setText(self, text):
        super().setText(text)
        self._offset = 0

    def enterEvent(self, event):
        if self.width() < self.sizeHint().width():
            self._timer.start(100)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._timer.stop()
        self._offset = 0
        super().leaveEvent(event)

    def _scroll(self):
        self._offset += 1
        text = self.text()
        if self._offset > len(text):
            self._offset = 0
        self.setText(text[self._offset:] + " " + text[:self._offset])