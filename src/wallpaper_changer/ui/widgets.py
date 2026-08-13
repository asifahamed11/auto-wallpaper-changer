from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from wallpaper_changer.ui.styles import ThemeColors


def _mix(first: QColor, second: QColor, progress: float) -> QColor:
    progress = min(1.0, max(0.0, progress))
    return QColor(
        round(first.red() + (second.red() - first.red()) * progress),
        round(first.green() + (second.green() - first.green()) * progress),
        round(first.blue() + (second.blue() - first.blue()) * progress),
        round(first.alpha() + (second.alpha() - first.alpha()) * progress),
    )


def _rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


class RoundedPanel(QFrame):
    """Antialiased surface with optional React Bits-style cursor spotlight."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        radius: float = 16.0,
        role: str = "surface",
        spotlight: bool = False,
    ):
        super().__init__(parent)
        self.radius = radius
        self.role = role
        self.spotlight = spotlight
        self.colors: ThemeColors | None = None
        self._spotlight_strength = 0.0
        self._spotlight_position = QPoint()
        self._spotlight_animation = QPropertyAnimation(self, b"spotlightStrength", self)
        self._spotlight_animation.setDuration(180)
        self._spotlight_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(33)
        self._cursor_timer.timeout.connect(self._track_cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)

    def set_theme(self, colors: ThemeColors) -> None:
        self.colors = colors
        self.update()

    def get_spotlight_strength(self) -> float:
        return self._spotlight_strength

    def set_spotlight_strength(self, value: float) -> None:
        self._spotlight_strength = value
        self.update()

    spotlightStrength = Property(float, get_spotlight_strength, set_spotlight_strength)

    def _animate_spotlight(self, target: float) -> None:
        self._spotlight_animation.stop()
        self._spotlight_animation.setStartValue(self._spotlight_strength)
        self._spotlight_animation.setEndValue(target)
        self._spotlight_animation.start()

    def _track_cursor(self) -> None:
        position = self.mapFromGlobal(QCursor.pos())
        if self.rect().contains(position):
            self._spotlight_position = position
            self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if self.spotlight:
            self._track_cursor()
            self._cursor_timer.start()
            self._animate_spotlight(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._cursor_timer.stop()
        if self.spotlight:
            self._animate_spotlight(0.0)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if self.colors is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        path = _rounded_path(rect, self.radius)
        fill = QColor(self.colors.surface_alt if self.role == "inset" else self.colors.surface)
        border = QColor(self.colors.border if self.role == "inset" else self.colors.subtle_border)
        painter.fillPath(path, fill)
        if self.spotlight and self._spotlight_strength > 0.001:
            gradient = QRadialGradient(self._spotlight_position, 240)
            glow = QColor(self.colors.accent)
            glow.setAlpha(round(52 * self._spotlight_strength))
            transparent = QColor(glow)
            transparent.setAlpha(0)
            gradient.setColorAt(0.0, glow)
            gradient.setColorAt(1.0, transparent)
            painter.fillPath(path, gradient)
        border = _mix(border, QColor(self.colors.accent), self._spotlight_strength * 0.28)
        painter.setPen(QPen(border, 1.0))
        painter.drawPath(path)


class RoundedLabel(QLabel):
    """Text/pixmap label that really clips its content to rounded corners."""

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        radius: float = 10.0,
        role: str = "inset",
        border: bool = True,
    ):
        super().__init__(text, parent)
        self.radius = radius
        self.role = role
        self.draw_border = border
        self.colors: ThemeColors | None = None
        self._display_pixmap = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def set_theme(self, colors: ThemeColors) -> None:
        self.colors = colors
        self.update()

    def setPixmap(self, pixmap: QPixmap | str) -> None:  # noqa: N802 - Qt API override
        self._display_pixmap = QPixmap(pixmap) if isinstance(pixmap, str) else QPixmap(pixmap)
        self.update()

    def pixmap(self) -> QPixmap:  # type: ignore[override]
        return QPixmap(self._display_pixmap)

    def clear(self) -> None:
        self._display_pixmap = QPixmap()
        self.setText("")
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if self.colors is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        path = _rounded_path(rect, self.radius)
        if self.role == "accent":
            fill = QColor(self.colors.accent)
            foreground = QColor(self.colors.accent_text)
            border = fill
        else:
            fill = QColor(self.colors.surface_alt)
            foreground = QColor(self.colors.muted if self.role == "pill" else self.colors.text)
            border = QColor(self.colors.border)
        painter.fillPath(path, fill)
        painter.save()
        painter.setClipPath(path)
        if not self._display_pixmap.isNull():
            pixmap = self._display_pixmap
            point = QPoint((self.width() - pixmap.width()) // 2, (self.height() - pixmap.height()) // 2)
            painter.drawPixmap(point, pixmap)
        elif self.text():
            painter.setPen(foreground)
            painter.setFont(self.font())
            painter.drawText(self.contentsRect(), int(self.alignment()), self.text())
        painter.restore()
        if self.draw_border:
            painter.setPen(QPen(border, 1.0))
            painter.drawPath(path)


class AnimatedButton(QPushButton):
    """Antialiased button with subtle hover and press motion."""

    def __init__(self, text: str = "", parent: QWidget | None = None, *, role: str = "default"):
        super().__init__(text, parent)
        self.role = role
        self.colors: ThemeColors | None = None
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._selection_progress = 0.0
        self._keyboard_focus = False
        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(150)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._press_animation = QPropertyAnimation(self, b"pressProgress", self)
        self._press_animation.setDuration(100)
        self._press_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._selection_animation = QPropertyAnimation(self, b"selectionProgress", self)
        self._selection_animation.setDuration(190)
        self._selection_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumHeight(38 if role != "nav" else 42)
        self.setMouseTracking(True)
        if role == "nav":
            self.toggled.connect(self._selection_changed)

    def set_theme(self, colors: ThemeColors) -> None:
        self.colors = colors
        self.update()

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = value
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def get_press_progress(self) -> float:
        return self._press_progress

    def set_press_progress(self, value: float) -> None:
        self._press_progress = value
        self.update()

    pressProgress = Property(float, get_press_progress, set_press_progress)

    def get_selection_progress(self) -> float:
        return self._selection_progress

    def set_selection_progress(self, value: float) -> None:
        self._selection_progress = value
        self.update()

    selectionProgress = Property(float, get_selection_progress, set_selection_progress)

    def _selection_changed(self, checked: bool) -> None:
        self._animate(self._selection_animation, self._selection_progress, 1.0 if checked else 0.0)

    @staticmethod
    def _animate(animation: QPropertyAnimation, start: float, target: float) -> None:
        animation.stop()
        animation.setStartValue(start)
        animation.setEndValue(target)
        animation.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if self.isEnabled():
            self._animate(self._hover_animation, self._hover_progress, 1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._animate(self._hover_animation, self._hover_progress, 0.0)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._animate(self._press_animation, self._press_progress, 1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._animate(self._press_animation, self._press_progress, 0.0)
        super().mouseReleaseEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self.update()

    def focusInEvent(self, event) -> None:
        self._keyboard_focus = event.reason() in {
            Qt.FocusReason.TabFocusReason,
            Qt.FocusReason.BacktabFocusReason,
            Qt.FocusReason.ShortcutFocusReason,
        }
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._keyboard_focus = False
        super().focusOutEvent(event)

    def sizeHint(self) -> QSize:
        font = QFont(self.font())
        font.setWeight(QFont.Weight.DemiBold)
        metrics = self.fontMetrics() if font == self.font() else QFontMetrics(font)
        horizontal_padding = 26 if self.role != "nav" else 28
        return QSize(max(70, metrics.horizontalAdvance(self.text()) + horizontal_padding), 42)

    def minimumSizeHint(self) -> QSize:
        """Keep layouts from squeezing translated labels outside the painted button."""
        return self.sizeHint()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if self.colors is None:
            return
        colors = self.colors
        transparent = QColor(0, 0, 0, 0)
        surface = QColor(colors.surface_alt)
        hover = QColor(colors.surface_hover)
        border = QColor(colors.border)
        accent = QColor(colors.accent)
        text = QColor(colors.text)
        muted = QColor(colors.muted)

        if self.role == "primary":
            fill = _mix(accent, accent.lighter(108), self._hover_progress)
            stroke = _mix(accent, QColor(colors.text), 0.18 + self._hover_progress * 0.42)
            foreground = QColor(colors.accent_text)
        elif self.role == "quiet":
            fill = _mix(transparent, surface, self._hover_progress)
            stroke = transparent
            foreground = _mix(muted, text, self._hover_progress)
        elif self.role == "nav":
            fill = _mix(
                _mix(transparent, surface, self._hover_progress),
                surface,
                self._selection_progress,
            )
            stroke = transparent
            foreground = _mix(
                _mix(muted, text, self._hover_progress),
                text,
                self._selection_progress,
            )
        else:
            fill = _mix(surface, hover, self._hover_progress)
            stroke = _mix(border, accent, self._hover_progress)
            foreground = QColor("#FF8E8E") if self.role == "danger" else text

        if not self.isEnabled():
            fill = QColor(colors.surface)
            stroke = QColor(colors.subtle_border)
            foreground = muted
        elif self._press_progress > 0:
            if self.role == "primary":
                fill = _mix(fill, fill.darker(110), self._press_progress)
            else:
                fill = _mix(fill, QColor(colors.border), self._press_progress * 0.28)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = 0.75 + self._press_progress * 0.35
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        radius = 10.0 if self.role == "nav" else 9.0
        path = _rounded_path(rect, radius)
        if fill.alpha() > 0:
            painter.fillPath(path, fill)
        if stroke.alpha() > 0:
            painter.setPen(QPen(stroke, 1.0))
            painter.drawPath(path)
        if self.role == "nav" and self.isChecked():
            indicator = QRectF(rect.left(), rect.top() + 10, 3.5, max(8.0, rect.height() - 20))
            painter.setPen(Qt.PenStyle.NoPen)
            indicator_color = QColor(accent)
            indicator_color.setAlpha(round(255 * self._selection_progress))
            painter.setBrush(indicator_color)
            painter.drawRoundedRect(indicator, 1.75, 1.75)
        if self.hasFocus() and self._keyboard_focus:
            focus = QColor(accent)
            focus.setAlpha(150)
            painter.setPen(QPen(focus, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(_rounded_path(rect.adjusted(2, 2, -2, -2), max(5.0, radius - 2)))
        painter.setPen(foreground)
        font = QFont(self.font())
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        text_rect = rect.adjusted(13, 0, -13, 0)
        alignment = Qt.AlignmentFlag.AlignVCenter
        alignment |= Qt.AlignmentFlag.AlignLeft if self.role == "nav" else Qt.AlignmentFlag.AlignHCenter
        painter.drawText(text_rect, alignment, self.text())


class RoundedComboBox(QComboBox):
    """A fully antialiased combo box with a crisp native-painted chevron."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.colors: ThemeColors | None = None
        self._hover_progress = 0.0
        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(150)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumHeight(38)
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        widest = max(
            (self.fontMetrics().horizontalAdvance(self.itemText(index)) for index in range(self.count())),
            default=0,
        )
        return QSize(max(112, min(280, widest + 58)), 38)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def set_theme(self, colors: ThemeColors) -> None:
        self.colors = colors
        self.update()

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = value
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def _animate_hover(self, target: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if self.isEnabled():
            self._animate_hover(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._animate_hover(0.0)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if self.colors is None:
            return
        colors = self.colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        fill = _mix(QColor(colors.surface), QColor(colors.surface_hover), self._hover_progress * 0.45)
        stroke = QColor(colors.accent if self.hasFocus() else colors.border)
        if not self.isEnabled():
            fill = QColor(colors.surface_alt)
            stroke = QColor(colors.subtle_border)
        path = _rounded_path(rect, 7)
        painter.fillPath(path, fill)
        painter.setPen(QPen(stroke, 2.0 if self.hasFocus() else 1.0))
        painter.drawPath(path)

        separator_x = rect.right() - 29
        separator = QColor(colors.border)
        separator.setAlpha(150)
        painter.setPen(QPen(separator, 1.0))
        painter.drawLine(round(separator_x), round(rect.top() + 1), round(separator_x), round(rect.bottom() - 1))
        foreground = QColor(colors.text if self.isEnabled() else colors.muted)
        painter.setPen(foreground)
        painter.setFont(self.font())
        text_rect = rect.adjusted(11, 0, -38, 0)
        text = self.fontMetrics().elidedText(self.currentText(), Qt.TextElideMode.ElideRight, round(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        chevron = QColor(colors.muted)
        painter.setPen(QPen(chevron, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center_x = rect.right() - 14.5
        center_y = rect.center().y()
        painter.drawLine(QPoint(round(center_x - 3), round(center_y - 1.5)), QPoint(round(center_x), round(center_y + 1.5)))
        painter.drawLine(QPoint(round(center_x), round(center_y + 1.5)), QPoint(round(center_x + 3), round(center_y - 1.5)))


class RoundedSpinBox(QSpinBox):
    """Antialiased spin box frame with functional, clean step arrows."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.colors: ThemeColors | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumHeight(38)
        self.lineEdit().setStyleSheet(
            "background: transparent; border: none; padding-left: 8px; padding-right: 34px;"
        )

    def set_theme(self, colors: ThemeColors) -> None:
        self.colors = colors
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if self.colors is None:
            return
        colors = self.colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        focused = self.hasFocus() or self.lineEdit().hasFocus()
        fill = QColor(colors.surface if self.isEnabled() else colors.surface_alt)
        stroke = QColor(colors.accent if focused else colors.border)
        path = _rounded_path(rect, 7)
        painter.fillPath(path, fill)
        painter.setPen(QPen(stroke, 2.0 if focused else 1.0))
        painter.drawPath(path)

        separator_x = rect.right() - 26
        painter.setPen(QPen(QColor(colors.border), 1.0))
        painter.drawLine(round(separator_x), round(rect.top() + 1), round(separator_x), round(rect.bottom() - 1))
        painter.drawLine(round(separator_x), round(rect.center().y()), round(rect.right() - 1), round(rect.center().y()))
        arrow = QColor(colors.muted)
        painter.setPen(QPen(arrow, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center_x = rect.right() - 13
        top_y = rect.top() + rect.height() * 0.27
        bottom_y = rect.top() + rect.height() * 0.73
        painter.drawLine(QPoint(round(center_x - 3), round(top_y + 2)), QPoint(round(center_x), round(top_y - 1)))
        painter.drawLine(QPoint(round(center_x), round(top_y - 1)), QPoint(round(center_x + 3), round(top_y + 2)))
        painter.drawLine(QPoint(round(center_x - 3), round(bottom_y - 2)), QPoint(round(center_x), round(bottom_y + 1)))
        painter.drawLine(QPoint(round(center_x), round(bottom_y + 1)), QPoint(round(center_x + 3), round(bottom_y - 2)))


class WallpaperItemDelegate(QStyledItemDelegate):
    """Antialiased gallery cards with clipped thumbnails."""

    def __init__(self, parent: QListWidget | None = None):
        super().__init__(parent)
        self.colors: ThemeColors | None = None

    def set_theme(self, colors: ThemeColors) -> None:
        self.colors = colors
        if self.parent():
            self.parent().viewport().update()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        del option, index
        return QSize(238, 184)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        if self.colors is None:
            super().paint(painter, option, index)
            return
        colors = self.colors
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect).adjusted(4.5, 4.5, -4.5, -4.5)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        fill = QColor(colors.surface_alt if selected or hovered else colors.surface)
        stroke = QColor(colors.accent if selected else colors.border if hovered else colors.subtle_border)
        painter.fillPath(_rounded_path(rect, 12), fill)
        painter.setPen(QPen(stroke, 2.0 if selected else 1.0))
        painter.drawPath(_rounded_path(rect, 12))

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_pixmap = icon.pixmap(420, 256) if isinstance(icon, QIcon) else QPixmap()
        text_top = rect.top() + 12
        if not icon_pixmap.isNull():
            image_rect = QRectF(rect.left() + 9, rect.top() + 9, rect.width() - 18, 116)
            clipped = _rounded_path(image_rect, 8)
            scaled = icon_pixmap.scaled(
                image_rect.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            source = QRectF(
                max(0, (scaled.width() - image_rect.width()) / 2),
                max(0, (scaled.height() - image_rect.height()) / 2),
                image_rect.width(),
                image_rect.height(),
            )
            painter.save()
            painter.setClipPath(clipped)
            painter.drawPixmap(image_rect, scaled, source)
            painter.restore()
            text_top = image_rect.bottom() + 7
        painter.setPen(QColor(colors.text if option.state & QStyle.StateFlag.State_Enabled else colors.muted))
        painter.setFont(option.font)
        text_rect = QRectF(rect.left() + 10, text_top, rect.width() - 20, rect.bottom() - text_top - 6)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
        )
        painter.restore()


class FadeStackedWidget(QStackedWidget):
    """React Bits-inspired short fade-and-slide content transition."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._animation: QParallelAnimationGroup | None = None

    def fade_to(self, index: int) -> None:
        if index < 0 or index >= self.count():
            return
        previous = self.currentIndex()
        if index == previous and self.currentWidget() is not None:
            return
        self.setCurrentIndex(index)
        page = self.currentWidget()
        if page is None:
            return
        effect = page.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)
        direction = 1 if index > previous else -1
        resting_position = page.pos()
        page.move(resting_position + QPoint(12 * direction, 0))
        effect.setOpacity(0.2)
        opacity = QPropertyAnimation(effect, b"opacity")
        opacity.setDuration(190)
        opacity.setStartValue(0.2)
        opacity.setEndValue(1.0)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        position = QPropertyAnimation(page, b"pos")
        position.setDuration(190)
        position.setStartValue(page.pos())
        position.setEndValue(resting_position)
        position.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity)
        group.addAnimation(position)
        group.finished.connect(lambda: page.move(resting_position))
        self._animation = group
        group.start()


class AnimatedStatusBar(QStatusBar):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.messageChanged.connect(self._reveal_message)

    def _reveal_message(self, _message: str) -> None:
        self._animation.stop()
        self._animation.setStartValue(0.4)
        self._animation.setEndValue(1.0)
        self._animation.start()
