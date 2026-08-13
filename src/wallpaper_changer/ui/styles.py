from __future__ import annotations


def stylesheet(theme: str, accent: str) -> str:
    dark = theme != "light"
    background = "#0B0D0C" if dark else "#F3F5F2"
    surface = "#121513" if dark else "#FFFFFF"
    surface_alt = "#1A1E1B" if dark else "#E9EEE9"
    surface_hover = "#222824" if dark else "#E0E7E1"
    text = "#F6F7F4" if dark else "#121513"
    muted = "#A5ABA7" if dark else "#5D665F"
    border = "#29302C" if dark else "#D6DDD8"
    subtle_border = "#202622" if dark else "#E4E9E5"
    accent_text = "#11130E"
    return f"""
    * {{
        font-family: "Segoe UI";
        font-size: 10pt;
        color: {text};
    }}
    QMainWindow, QDialog, QWidget#AppRoot {{ background: {background}; }}
    QWidget#Page, QWidget#ContentSurface {{ background: transparent; }}
    QFrame#NavRail {{
        background: {surface}; border: 1px solid {subtle_border}; border-radius: 18px;
    }}
    QLabel#BrandMark {{ background: {accent}; color: {accent_text}; border-radius: 10px; }}
    QLabel#BrandTitle {{ font-size: 12pt; font-weight: 700; }}
    QLabel#PageTitle {{ font-size: 22pt; font-weight: 720; }}
    QLabel#SectionTitle {{ font-size: 13pt; font-weight: 650; }}
    QLabel#HeroTitle {{ font-size: 16pt; font-weight: 700; }}
    QLabel#Muted {{ color: {muted}; }}
    QLabel#PageSubtitle {{ color: {muted}; font-size: 10pt; }}
    QLabel#StatusPill {{
        background: {surface_alt}; color: {muted}; border: 1px solid {border};
        border-radius: 9px; padding: 7px 9px;
    }}
    QFrame#Card {{ background: {surface}; border: 1px solid {subtle_border}; border-radius: 16px; }}
    QFrame#Inset {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 12px; }}
    QLabel#Preview {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 13px; }}
    QPushButton#NavButton {{
        background: transparent; border: none; border-radius: 10px; color: {muted};
        padding: 11px 13px; text-align: left; font-weight: 600;
    }}
    QPushButton#NavButton:hover {{ background: {surface_alt}; color: {text}; }}
    QPushButton#NavButton:checked {{
        background: {surface_alt}; color: {text}; border-left: 3px solid {accent};
        padding-left: 10px;
    }}
    QPushButton {{
        background: {surface_alt}; border: 1px solid {border}; border-radius: 9px;
        padding: 9px 14px; font-weight: 600;
    }}
    QPushButton:hover {{ background: {surface_hover}; border-color: {accent}; }}
    QPushButton:pressed {{ background: {border}; }}
    QPushButton#Primary {{ background: {accent}; color: {accent_text}; border-color: {accent}; }}
    QPushButton#Primary:hover {{ background: {accent}; border-color: {text}; }}
    QPushButton#Quiet {{ background: transparent; border-color: transparent; color: {muted}; }}
    QPushButton#Quiet:hover {{ background: {surface_alt}; color: {text}; }}
    QPushButton#Danger {{ color: #FF8E8E; }}
    QPushButton:disabled {{ background: {surface}; color: {muted}; border-color: {subtle_border}; }}
    QLineEdit, QComboBox, QSpinBox {{
        background: {surface}; border: 1px solid {border}; border-radius: 8px;
        padding: 8px 10px; min-height: 20px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {accent}; }}
    QComboBox QAbstractItemView {{ background: {surface}; border: 1px solid {border}; selection-background-color: {surface_alt}; }}
    QComboBox:disabled, QSpinBox:disabled {{ color: {muted}; background: {surface_alt}; }}
    QCheckBox {{ spacing: 9px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QListWidget {{ background: transparent; border: none; outline: none; }}
    QListWidget::item {{ background: {surface}; border: 1px solid {subtle_border}; border-radius: 12px; padding: 7px; margin: 4px; }}
    QListWidget::item:hover {{ border-color: {border}; background: {surface_alt}; }}
    QListWidget::item:selected {{ border: 2px solid {accent}; background: {surface_alt}; }}
    QScrollBar:vertical {{ width: 10px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 28px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QProgressBar#BusyBar {{ background: {surface_alt}; border: none; border-radius: 2px; max-height: 4px; }}
    QProgressBar#BusyBar::chunk {{ background: {accent}; border-radius: 2px; }}
    QToolTip {{ background: {surface}; color: {text}; border: 1px solid {border}; padding: 6px; }}
    QStatusBar {{ background: {background}; color: {muted}; border-top: 1px solid {subtle_border}; }}
    QStatusBar::item {{ border: none; }}
    """
