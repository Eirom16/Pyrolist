from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPoint, Qt, QPropertyAnimation
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QVBoxLayout, QWidget


class GlassPanel(QWidget):
    def __init__(self, parent=None, blur_radius: int = 20):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._opacity = 0.0
        self._blur_radius = blur_radius

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        self._opacity_anim = QPropertyAnimation(self, b"panel_opacity", self)
        self._opacity_anim.setDuration(200)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._pos_anim = QPropertyAnimation(self, b"pos", self)
        self._pos_anim.setDuration(200)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.setWindowOpacity(value)

    panel_opacity = Property(float, _get_opacity, _set_opacity)

    def popup_at(self, pos: QPoint) -> None:
        self.move(pos.x(), pos.y() + 10)
        self.show()
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()
        self._pos_anim.stop()
        self._pos_anim.setStartValue(QPoint(pos.x(), pos.y() + 10))
        self._pos_anim.setEndValue(pos)
        self._pos_anim.start()

    def dismiss(self) -> None:
        try:
            self._opacity_anim.finished.disconnect()
        except RuntimeError:
            pass
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self.close)
        self._opacity_anim.start()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Query tokens.CURRENT dynamically for elevated background
        from pyrolist.ui.design import tokens
        bg_col = QColor(tokens.CURRENT.bg_elevated)
        bg_col.setAlpha(230)
        
        painter.setBrush(QBrush(bg_col))
        painter.drawRoundedRect(rect, 16, 16)
        
        # Build gradient borders with the dynamic accent color
        accent_col = QColor(tokens.CURRENT.accent)
        border = QLinearGradient(0, 0, 0, self.height())
        border.setColorAt(0, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 80))
        border.setColorAt(0.6, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 22))
        border.setColorAt(1, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 10))
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(border), 1.0))
        painter.drawRoundedRect(rect, 16, 16)
        painter.end()

