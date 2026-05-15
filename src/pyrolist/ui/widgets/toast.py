from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QTimer, Qt, QPropertyAnimation
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon


class ToastNotification(QWidget):
    _COLORS = {
        "success": ("#34D399", "#0A2E1E", "check_circle"),
        "error": ("#F87171", "#2E0A0A", "error"),
        "info": ("#60A5FA", "#0A1A2E", "info"),
        "warning": ("#FBBF24", "#2E1E0A", "warning"),
    }

    def __init__(self, parent: QWidget, message: str, kind: str = "info"):
        super().__init__(parent, Qt.WindowType.SubWindow)
        accent, bg, icon_name = self._COLORS.get(kind, self._COLORS["info"])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 20, 12)
        layout.setSpacing(10)
        layout.addWidget(Icon.label(icon_name, 20, accent))
        msg = QLabel(message)
        msg.setFont(AppFont.body(13))
        msg.setWordWrap(True)
        msg.setMaximumWidth(280)
        msg.setStyleSheet("color: #F1F0FF; background: transparent;")
        layout.addWidget(msg)
        self.setStyleSheet(f"ToastNotification {{ background-color: {bg}; border: 1px solid {accent}66; border-radius: 14px; }}")
        self.adjustSize()
        parent_rect = parent.rect()
        self.move(max(20, parent_rect.width() - self.width() - 20), max(20, parent_rect.height() - self.height() - 96))
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._in_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._in_anim.setDuration(260)
        self._in_anim.setStartValue(0.0)
        self._in_anim.setEndValue(1.0)
        self._in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._in_anim.start()
        QTimer.singleShot(3500, self._dismiss)

    def _dismiss(self) -> None:
        self._out_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._out_anim.setDuration(320)
        self._out_anim.setStartValue(self.windowOpacity())
        self._out_anim.setEndValue(0.0)
        self._out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._out_anim.finished.connect(self.deleteLater)
        self._out_anim.start()

    @staticmethod
    def show(parent: QWidget, message: str, kind: str = "info") -> "ToastNotification":
        return ToastNotification(parent, message, kind)

