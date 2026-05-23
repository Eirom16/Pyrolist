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
        
        # Base style, size will be overridden if setFont is called
        self.setStyleSheet(f"QPushButton {{ border: none; background: transparent; font-family: 'Material Symbols Rounded'; font-size: {size // 2 + 4}px; }}")

        self._scale = 1.0
        
    def setFont(self, font):
        super().setFont(font)
        sz = font.pixelSize() if font.pixelSize() > 0 else font.pointSize()
        fam = font.family()
        self.setStyleSheet(f"QPushButton {{ border: none; background: transparent; font-family: '{fam}'; font-size: {sz}px; }}")
        self._bg_anim = QPropertyAnimation(self, b"bg_opacity", self)
        self._bg_anim.setDuration(150)
        self._bg_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._scale_anim = QPropertyAnimation(self, b"icon_scale", self)
        self._scale_anim.setDuration(250)

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.update()

    def _get_bg(self) -> float:
        return self._bg_opacity

    def _set_bg(self, value: float) -> None:
        self._bg_opacity = value
        self.update()

    bg_opacity = Property(float, _get_bg, _set_bg)

    def _get_scale(self) -> float:
        return self._scale

    def _set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    icon_scale = Property(float, _get_scale, _set_scale)

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

    def mousePressEvent(self, event):
        self._scale_anim.stop()
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.setEndValue(0.75)
        self._scale_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._scale_anim.stop()
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        from pyrolist.ui.design import tokens
        active_color = QColor(tokens.CURRENT.accent)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Apply scaling from center
        w, h = self.width(), self.height()
        painter.translate(w / 2, h / 2)
        painter.scale(self._scale, self._scale)
        painter.translate(-w / 2, -h / 2)

        if self._bg_opacity > 0:
            color = QColor(active_color if self._is_active else QColor(tokens.CURRENT.text_primary))
            color.setAlphaF(self._bg_opacity * 0.12)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(self.rect())
            
        if self._is_active:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(active_color))
            painter.drawEllipse(w // 2 - 3, h - 6, 6, 4)
            
        if self.text():
            painter.setFont(self.font())
            text_color = self.palette().color(self.foregroundRole())
            # For specific elements that force color via stylesheet, we might need to parse it,
            # but usually foregroundRole is correct or text_primary
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        elif not self.icon().isNull():
            # Fallback for QIcon if set
            icon_size = self.iconSize()
            x = (w - icon_size.width()) // 2
            y = (h - icon_size.height()) // 2
            self.icon().paint(painter, x, y, icon_size.width(), icon_size.height())
            
        painter.end()

