from dataclasses import dataclass
from PyQt5.QtGui import QFont, QPalette, QGuiApplication, QColor
from PyQt5.QtWidgets import QApplication


# ---- Theming ----
@dataclass(frozen=True)
class Theme:
    name: str
    font_family: str
    font_size: int
    widget_padding: int
    widget_radius: int
    bg: str
    text: str
    panel: str
    border: str
    input_bg: str
    button_bg: str
    button_bg_hover: str
    button_bg_pressed: str
    button_border: str
    accent1: str
    accent2: str
    selection: str
    user_bubble_bg: str
    assistant_bubble_bg: str


class ThemeManager:
    DARK = Theme(
        name="Dark",
        font_family="Inter, Segoe UI, Roboto, Arial",
        font_size=QGuiApplication.font().pointSize(),
        widget_padding=10,
        widget_radius=20,
        bg="#0f1115",
        text="#eaeef2",
        panel="rgba(47, 47, 47, 0.4);",
        border="rgba(182, 182, 196, 0.25);",
        input_bg="rgba(85, 82, 82, 0.2)",
        button_bg="rgba(85, 82, 82, 0.2)",
        button_bg_hover="#252d40",
        button_bg_pressed="#191e2a",
        button_border="#2a3142",
        accent1="#3857ff",
        accent2="#3a5fff",
        selection="#2a3553",
        user_bubble_bg="rgba(78, 44, 102, 0.25);",
        assistant_bubble_bg="rgba(90, 87, 63, 0.35);",
    )

    LIGHT = Theme(
        name="Light",
        font_family="Inter, Segoe UI, Roboto, Arial",
        font_size=25,
        widget_padding=8,
        widget_radius=10,
        bg="#ffffff",
        text="#202124",
        panel="#f3f5f7",
        border="#dfe3ea",
        input_bg="#ffffff",
        button_bg="#f6f7fb",
        button_bg_hover="#eef0f6",
        button_bg_pressed="#e2e6ef",
        button_border="#d9deea",
        accent1="#335cff",
        accent2="#2a50f8",
        selection="#dbe4ff",
        user_bubble_bg="qlineargradient( x1:0, y1:0, x2:1, y2:1, stop:0 #9bb5ff, stop:1 #c79fff )",
        assistant_bubble_bg="qlineargradient( x1:0, y1:0, x2:1, y2:1, stop:0 #dfe3e6, stop:1 #bfc4c9 )"
    )

    @staticmethod
    def apply_palette(app: QApplication, theme: Theme) -> None:
        app.setStyle("Fusion")
        pal = app.palette()
        colors = {
            QPalette.Window: theme.bg,
            QPalette.WindowText: theme.text,
            QPalette.Base: theme.input_bg,
            QPalette.AlternateBase: theme.panel,
            QPalette.ToolTipBase: theme.panel,
            QPalette.ToolTipText: theme.text,
            QPalette.Text: theme.text,
            QPalette.Button: theme.button_bg,
            QPalette.ButtonText: theme.text,
            QPalette.BrightText: "#ffffff",
            QPalette.Highlight: theme.accent2,
            QPalette.HighlightedText: "#ffffff",
            QPalette.Link: theme.accent1,
            QPalette.LinkVisited: theme.selection,
            QPalette.Shadow: theme.border,
        }
        for role, color in colors.items():
            pal.setColor(role, QColor(color))
        app.setPalette(pal)
        app.setFont(QFont(theme.font_family, theme.font_size))

    @staticmethod
    def stylesheet(theme: Theme) -> str:
        return f"""
        QWidget {{ font-family: {theme.font_family}; font-size: {theme.font_size}px; }}
        QMainWindow {{ background: {theme.bg}; color: {theme.text}; }}
        QLabel {{ color: {theme.text}; line-height: 1.5em; }}
        QTextBrowser, QSpinBox, QDoubleSpinBox, QTextEdit, QLineEdit {{
            background: {theme.input_bg};
            color: {theme.text};
            border: 2px solid {theme.border};
            border-radius: {theme.widget_radius}px;
            padding: {theme.widget_padding}px {theme.widget_padding}px;
        }}
        QComboBox {{
            background: {theme.input_bg};
            color: {theme.text};
            border: 2px solid {theme.border};
            border-radius: {theme.widget_radius}px;
            padding: {theme.widget_padding}px {theme.widget_padding}px;
            min-height: 28px;
            selection-background-color: rgba(255, 85, 0, 0.2);
        }}

        QComboBox:hover {{
            background: #111827;
        }}
        QComboBox:disabled {{
            background: #111827;
            color: #6b7280;
            border-color: #1f2937;
        }}

        /* Editable mode (when setEditable(True)) */
        QComboBox::editable {{
            background: transparent;
        }}

        /* Drop-down button & arrow */
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 60px;
            border-left: 1px solid #374151;
        }}
        QComboBox::down-arrow {{
            image: url("star2.png");
            width: 60px;
            height: 60px;
        }}

        /* Popup list view */
        QComboBox QAbstractItemView {{
            background: {theme.input_bg};
            border: 1px solid {theme.border};
            border-radius: {theme.widget_radius}px;
            padding: 4px 0;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 28px;
            padding: 4px 10px;
            border-radius: {theme.widget_radius}px;
        }}

        QPushButton {{
            background: {theme.button_bg};
            color: {theme.text};
            border: 1px solid {theme.button_border};
            border-radius: {theme.widget_radius}px;
            padding: {theme.widget_padding}px {theme.widget_padding}px;
        }}
        QToolButton {{
            background: {theme.button_bg};
            color: {theme.text};
            border: 1px solid {theme.button_border};
            border-radius: 6px;
            padding: {theme.widget_padding}px {theme.widget_padding}px;
        }}

        QPushButton:hover, QToolButton:hover {{
            background: {theme.button_bg_hover};
        }}

        QPushButton:pressed, QToolButton:pressed {{
            background: {theme.button_bg_pressed};
        }}
        QPushButton:disabled {{ color: #8b93a6; }}

        /* User bubble: ChatGPT style */
        #ai_bubble[variant="user"] {{
            background: {theme.user_bubble_bg};
            color: {theme.text};
            border-radius: 30px;
            border: 3px solid {theme.border};
        }}
        /* Assistant bubble: ChatGPT style */
        #ai_bubble[variant="assistant"] {{
            background: {theme.assistant_bubble_bg};
            color: {theme.text};
            border-radius: 50px;
            border: 1px solid {theme.border};
        }}

        QTextBrowser#ai_bubble {{
            background: rgba(85, 82, 82, 0.7);
            font-family: Inter, Segoe UI, Roboto, Arial;
            font-size: {theme.font_size}px;
            color: #eaeef2;
        }}    

        QWidget#inputPane {{
            background: {theme.panel};
            border-top: 2px solid rgba(255, 255, 255, 0.2);
            padding: 8px;
        }}

        QTextBrowser QScrollBar:vertical {{
            width: 0px;
            margin: 0;
            background: transparent;
        }}
        QTextBrowser QScrollBar:horizontal {{
            height: 0px;
            margin: 0;
            background: transparent;
        }}

        QWidget#central {{ 
        border-image: url("./Dependencies/bg.jpg") 0 0 0 0 stretch stretch; 
        }}

        QWidget#chatContent {{ background: Transparent; }}
        QWidget#chatScroll {{ background: Transparent; }}


        """