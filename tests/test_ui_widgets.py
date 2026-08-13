from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, QPoint, Qt  # noqa: E402
from PySide6.QtGui import QColor, QEnterEvent, QMouseEvent, QPixmap  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from wallpaper_changer.ui.styles import theme_colors  # noqa: E402
from wallpaper_changer.ui.widgets import (  # noqa: E402
    AnimatedButton,
    RoundedComboBox,
    RoundedLabel,
    RoundedPanel,
    RoundedSpinBox,
)


@pytest.fixture
def application():
    return QApplication.instance() or QApplication([])


def test_rounded_surfaces_have_transparent_outer_corners(application):
    colors = theme_colors("dark", "#F7F06D")
    panel = RoundedPanel(radius=18)
    panel.resize(140, 90)
    panel.set_theme(colors)
    panel.show()
    application.processEvents()
    image = panel.grab().toImage()
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(image.width() // 2, image.height() // 2).alpha() == 255

    preview = RoundedLabel(radius=16)
    preview.resize(140, 90)
    preview.set_theme(colors)
    pixmap = QPixmap(180, 120)
    pixmap.fill(QColor("#FF0000"))
    preview.setPixmap(pixmap)
    preview.show()
    application.processEvents()
    preview_image = preview.grab().toImage()
    assert preview_image.pixelColor(0, 0).alpha() == 0
    assert preview_image.pixelColor(70, 45).red() > 240


def test_spotlight_is_visible_and_dark_accents_keep_contrast(application):
    colors = theme_colors("dark", "#152A45")
    assert colors.accent_text == "#FFFFFF"
    assert theme_colors("light", "#F7F06D").accent_text == "#11130E"

    panel = RoundedPanel(radius=16, spotlight=True)
    panel.resize(240, 140)
    panel.set_theme(colors)
    panel._spotlight_position = QPoint(120, 70)
    panel.show()
    application.processEvents()
    base = panel.grab().toImage().pixelColor(120, 70)
    panel.set_spotlight_strength(1.0)
    highlighted = panel.grab().toImage().pixelColor(120, 70)
    assert highlighted != base
    assert highlighted.lightness() > base.lightness()


def test_button_hover_press_and_selection_states_animate(application):
    button = AnimatedButton("Automation", role="nav")
    button.setCheckable(True)
    button.set_theme(theme_colors("dark", "#F7F06D"))
    button.resize(160, 42)
    button.show()
    application.processEvents()

    button.setChecked(True)
    enter = QEnterEvent(QPoint(10, 10), QPoint(10, 10), QPoint(10, 10))
    application.sendEvent(button, enter)
    press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPoint(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    application.sendEvent(button, press)
    QTest.qWait(220)
    assert button.get_selection_progress() > 0
    assert button.get_hover_progress() > 0
    assert button.get_press_progress() > 0


def test_button_minimum_size_keeps_its_full_label_visible(application):
    button = AnimatedButton("Pause until tomorrow")
    button.set_theme(theme_colors("dark", "#F7F06D"))
    button.show()
    application.processEvents()

    assert button.minimumSizeHint() == button.sizeHint()
    assert button.minimumSizeHint().width() >= button.fontMetrics().horizontalAdvance(button.text()) + 26


def test_custom_combo_and_spin_controls_remain_interactive(application):
    colors = theme_colors("dark", "#F7F06D")
    combo = RoundedComboBox()
    combo.addItems(["Random", "Nature"])
    combo.set_theme(colors)
    combo.resize(220, 38)
    combo.show()
    combo.showPopup()
    application.processEvents()
    assert combo.view().isVisible()
    combo.hidePopup()
    assert combo.sizeHint().width() >= combo.fontMetrics().horizontalAdvance("Nature") + 50

    spin = RoundedSpinBox()
    spin.setRange(0, 10)
    spin.set_theme(colors)
    spin.resize(220, 38)
    spin.show()
    application.processEvents()
    QTest.mouseClick(spin, Qt.MouseButton.LeftButton, pos=QPoint(207, 8))
    assert spin.value() == 1
