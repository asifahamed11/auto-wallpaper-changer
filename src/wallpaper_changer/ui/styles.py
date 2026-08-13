from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThemeColors:
    background: str
    surface: str
    surface_alt: str
    surface_hover: str
    text: str
    muted: str
    border: str
    subtle_border: str
    accent: str
    accent_text: str


def _contrast_text(accent: str) -> str:
    try:
        red = int(accent[1:3], 16) / 255
        green = int(accent[3:5], 16) / 255
        blue = int(accent[5:7], 16) / 255
    except (ValueError, IndexError):
        return "#11130E"

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)
    return "#11130E" if luminance > 0.42 else "#FFFFFF"


def theme_colors(theme: str, accent: str) -> ThemeColors:
    dark = theme != "light"
    return ThemeColors(
        background="#0B0D0C" if dark else "#F3F5F2",
        surface="#121513" if dark else "#FFFFFF",
        surface_alt="#1A1E1B" if dark else "#E9EEE9",
        surface_hover="#222824" if dark else "#E0E7E1",
        text="#F6F7F4" if dark else "#121513",
        muted="#A5ABA7" if dark else "#5D665F",
        border="#29302C" if dark else "#D6DDD8",
        subtle_border="#202622" if dark else "#E4E9E5",
        accent=accent,
        accent_text=_contrast_text(accent),
    )


def stylesheet(theme: str, accent: str) -> str:
    colors = theme_colors(theme, accent)
    return f"""
    * {{
        font-family: "Segoe UI";
        font-size: 10pt;
        color: {colors.text};
    }}
    QMainWindow, QDialog, QWidget#AppRoot {{ background: {colors.background}; }}
    QWidget#Page, QWidget#ContentSurface, QWidget#ScrollContent,
    QScrollArea#PageScroll, QScrollArea#PageScroll > QWidget > QWidget {{
        background: transparent; border: none;
    }}
    RoundedPanel, RoundedLabel, AnimatedButton, RoundedComboBox, RoundedSpinBox {{
        background: transparent; border: none;
    }}
    QLabel#BrandTitle {{ font-size: 12pt; font-weight: 700; }}
    QLabel#PageTitle {{ font-size: 22pt; font-weight: 720; }}
    QLabel#SectionTitle {{ font-size: 13pt; font-weight: 650; }}
    QLabel#HeroTitle {{ font-size: 16pt; font-weight: 700; }}
    QLabel#Muted {{ color: {colors.muted}; }}
    QLabel#PageSubtitle {{ color: {colors.muted}; font-size: 10pt; }}
    AnimatedButton {{ padding: 0; font-weight: 600; }}
    QLineEdit {{
        background: {colors.surface}; border: 1px solid {colors.border}; border-radius: 7px;
        padding: 8px 10px; min-height: 20px;
    }}
    QLineEdit:focus {{ border: 2px solid {colors.accent}; }}
    RoundedComboBox QAbstractItemView {{
        background: {colors.surface}; border: 1px solid {colors.border};
        selection-background-color: {colors.surface_alt};
    }}
    QCheckBox {{ spacing: 9px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QListWidget {{ background: transparent; border: none; outline: none; }}
    QListWidget::item {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ width: 10px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: {colors.border}; border-radius: 5px; min-height: 28px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QProgressBar#BusyBar {{
        background: {colors.surface_alt}; border: none; border-radius: 2px; max-height: 4px;
    }}
    QProgressBar#BusyBar::chunk {{ background: {colors.accent}; border-radius: 2px; }}
    QToolTip {{
        background: {colors.surface}; color: {colors.text}; border: 1px solid {colors.border}; padding: 6px;
    }}
    QStatusBar {{
        background: {colors.background}; color: {colors.muted};
        border-top: 1px solid {colors.subtle_border};
    }}
    QStatusBar::item {{ border: none; }}
    """
