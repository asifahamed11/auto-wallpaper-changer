from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget


class FadeStackedWidget(QStackedWidget):
    """A tiny, GPU-friendly page transition for the main navigation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation: QPropertyAnimation | None = None

    def fade_to(self, index: int) -> None:
        if index < 0 or index >= self.count():
            return
        if index == self.currentIndex() and self.currentWidget() is not None:
            return
        self.setCurrentIndex(index)
        page = self.currentWidget()
        if page is None:
            return
        effect = page.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)
        effect.setOpacity(0.35)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(150)
        animation.setStartValue(0.35)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation = animation
        animation.start()
