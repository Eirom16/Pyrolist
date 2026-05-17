from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QSize, Qt, QPropertyAnimation
from PySide6.QtGui import QBrush, QColor, QEnterEvent, QIcon, QPainter, QPaintEvent
from PySide6.QtWidgets import QPushButton


class IconButton(QPushButton):
    def __init__(
        self,
        icon: QIcon | None = None,
        size: int = 40,
        active_color: str = "#A78BFA",
        parent=None,
    ):
        super().__init__(parent)
        self.setFixedSize(QSize(size, size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active_color = QColor(active_color)
        self._is_active = False
        self._bg_opacity = 0.0
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(size - 12, size - 12))
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

        self._bg_anim = QPropertyAnimation(self, b"bg_opacity", self)
        self._bg_anim.setDuration(150)
        self._bg_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.update()

    def _get_bg(self) -> float:
        return self._bg_opacity

    def _set_bg(self, value: float) -> None:
        self._bg_opacity = value
        self.update()

    bg_opacity = Property(float, _get_bg, _set_bg)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._bg_anim.stop()
        self._bg_anim.setStartValue(self._bg_opacity)
        self._bg_anim.setEndValue(1.0)
        self._bg_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._bg_anim.stop()
        self._bg_anim.setStartValue(self._bg_opacity)
        self._bg_anim.setEndValue(0.0)
        self._bg_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        from pyrolist.ui.design import tokens
        active_color = QColor(tokens.CURRENT.accent)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._bg_opacity > 0:
            color = QColor(active_color if self._is_active else QColor(255, 255, 255))
            color.setAlphaF(self._bg_opacity * 0.12)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(self.rect())
        if self._is_active:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(active_color))
            painter.drawEllipse(self.width() // 2 - 3, self.height() - 6, 6, 4)
        painter.end()
        super().paintEvent(event)

