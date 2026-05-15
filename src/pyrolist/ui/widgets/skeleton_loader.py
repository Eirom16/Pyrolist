from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, Qt, QPropertyAnimation
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPaintEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget


class SkeletonBlock(QWidget):
    def __init__(self, width: int, height: int, radius: int = 8, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._radius = radius
        self._shimmer_pos = -0.3
        self._anim = QPropertyAnimation(self, b"shimmer", self)
        self._anim.setStartValue(-0.3)
        self._anim.setEndValue(1.3)
        self._anim.setDuration(1500)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def _get_shimmer(self) -> float:
        return self._shimmer_pos

    def _set_shimmer(self, value: float) -> None:
        self._shimmer_pos = value
        self.update()

    shimmer = Property(float, _get_shimmer, _set_shimmer)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 56)))
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)
        w = self.width()
        shimmer_w = w * 0.4
        x = self._shimmer_pos * (w + shimmer_w) - shimmer_w
        gradient = QLinearGradient(x, 0, x + shimmer_w, 0)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.5, QColor(167, 139, 250, 32))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)
        painter.end()


def make_song_skeleton(parent=None) -> QWidget:
    widget = QWidget(parent)
    row = QHBoxLayout(widget)
    row.setContentsMargins(12, 8, 12, 8)
    row.setSpacing(12)
    row.addWidget(SkeletonBlock(48, 48, 8))
    info = QVBoxLayout()
    info.setSpacing(6)
    info.addWidget(SkeletonBlock(180, 14, 7))
    info.addWidget(SkeletonBlock(110, 11, 7))
    row.addLayout(info)
    row.addStretch()
    row.addWidget(SkeletonBlock(50, 11, 7))
    return widget


class SkeletonListLoader(QWidget):
    def __init__(self, row_count: int = 6, skeleton_factory=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        factory = skeleton_factory or make_song_skeleton
        for _ in range(row_count):
            layout.addWidget(factory(self))
        layout.addStretch()

