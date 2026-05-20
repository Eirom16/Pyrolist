from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPoint, Qt, QPropertyAnimation
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget, QGraphicsOpacityEffect


class GlassPanel(QWidget):
    def __init__(self, parent=None, blur_radius: int = 20):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._opacity = 0.0
        self._blur_radius = blur_radius
        self._trigger_widget = None

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

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
        self._opacity_effect.setOpacity(value)
        self.update()

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
        self._opacity_anim.setStartValue(self._opacity)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self.close)
        self._opacity_anim.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        from PySide6.QtWidgets import QApplication
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QWidget
        if event.type() == QEvent.Type.MouseButtonPress:
            pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            local_pos = self.mapFromGlobal(pos)
            if not self.rect().contains(local_pos):
                trigger = getattr(self, "_trigger_widget", None)
                if trigger and isinstance(trigger, QWidget):
                    trigger_local = trigger.mapFromGlobal(pos)
                    if trigger.rect().contains(trigger_local):
                        self.hide()
                        return False
                self.dismiss()
        return super().eventFilter(watched, event)

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


