from __future__ import annotations

import math
import webbrowser
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer, QEvent, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QFont, QPalette, QColor, QTextOption, QGuiApplication, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpacerItem, QWidget, QTextBrowser, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QToolButton,
    QSizePolicy
)
from markdown_it import MarkdownIt

from urllib.parse import urlparse

def safe_open(url):
    scheme = urlparse(url.toString()).scheme.lower()
    if scheme in ("http", "https"):
        webbrowser.open(url.toString())
    else:
        print(f"Ignored unsafe link: {url.toString()}")

# markdown parser is stateless and shared
md = MarkdownIt()
md = md.disable(["html_block", "html_inline"])

# ---- Light-weight role identifiers ----
@dataclass(frozen=True)
class ChatRole:
    USER: str = "user"
    ASSISTANT: str = "assistant"
    SYSTEM: str = "system"

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
        panel="rgba(47, 47, 47, 0.25);",
        border="rgba(182, 182, 196, 0.25);",
        input_bg="Transparent",
        button_bg="Transparent",
        button_bg_hover="#252d40",
        button_bg_pressed="#191e2a",
        button_border="#2a3142",
        accent1="#3857ff",
        accent2="#3a5fff",
        selection="#2a3553",
        user_bubble_bg="rgba(78, 44, 102, 0.25);",
        assistant_bubble_bg="rgba(90, 87, 63, 0.25);",
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
            selection-background-color: rgba(255, 85, 0, 0.3);
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
            background: rgba(85, 82, 82, 0.61);
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
        border-image: url("bg.jpg") 0 0 0 0 stretch stretch; 
        }}
        
        QWidget#chatContent {{ background: Transparent; }}
        QWidget#chatScroll {{ background: Transparent; }}

        
        """


class HSpacer(QWidget):
    """
    Horizontal spacer that can be used to help align widgets
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # todo make sure this is okay
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # don’t block clicks
        self.setStyleSheet("background: transparent; border: none;")

class MinimumSizeBrowser(QTextBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setViewportMargins(20, 20, 40, 20)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # simple cache for heightForWidth

       # self.setMinimumWidth(500) # gotta set it to something to start
        self.current_w = 1
        self.current_h = 1

        # Wrap to the widget width when constrained by the layout.
        self.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.anchorClicked.connect(safe_open)

        self.document().setUndoRedoEnabled(False)
        self.setFrameShape(QFrame.NoFrame)
        # We resize instead of scrolling.
        self.setObjectName("ai_bubble")

        self.setAcceptRichText(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.textChanged.connect(self._recompute_dimensions)
        self.textChanged.connect(lambda: QTimer.singleShot(0, self.ensureCursorVisible))

        self.document().setDocumentMargin(0)

        QTimer.singleShot(0, self._recompute_dimensions)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(self.current_w, self.current_h)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return self.sizeHint()

    def check_if_size_changed(self):
        different = False
        w = self.compute_min_w()

        if self.current_w != w:
            self.current_w = w
            different =  True

        h = self.compute_min_h(w)

        if self.current_h != h:
            self.current_h = h
            different = True

        return different

    def compute_min_w(self):
        extra_w, _ = self._extra_margins()
        doc = self.document()

        old_tw = doc.textWidth()
        try:
            doc.setTextWidth(-1)  # "unbounded"; lets idealWidth reflect natural width
            ideal_content_w = math.ceil(doc.idealWidth())
        finally:
            doc.setTextWidth(old_tw)

        w = int(min(ideal_content_w + extra_w, self.maximumWidth()))

        if w >= self.maximumWidth():
            w = self.maximumWidth()

        if w < self.minimumWidth():
            w = self.minimumWidth()

        return w

    def compute_min_h(self, w):
        """ Return total widget height required to show all content at width *w*."""
        if w <= 0:
            # defensive: avoid negative sizes in pathological layouts
            print("compute_min_h received a negative width")
            return super().height()

        if w < self.minimumWidth():
            print(f"Width given is less than min allowed! w given is {w}")
            w = self.minimumWidth()

        if w > self.maximumWidth():
            print(f"Width given is greater than max allowed! w given is {w}")
            w = self.maximumWidth()

        extra_w, extra_h = self._extra_margins()
        content_w = max(0, w - extra_w)
        doc = self.document()
        old_tw = doc.textWidth()
        try:
            doc.setTextWidth(content_w)  #contentw slightly too big
            doc_h = math.ceil(doc.size().height())
        finally:
            doc.setTextWidth(old_tw)

        total_h = int(doc_h + extra_h)

        # you must obey your boundaries!

        if total_h < self.minimumHeight():
            total_h = self.minimumHeight()

        if total_h > self.maximumHeight():
            total_h = self.maximumHeight()

        return total_h

    def _recompute_dimensions(self):
        if self.check_if_size_changed():
            self.updateGeometry()


    # --- utilities ------------------------------------------------------
    # I've seen that something is off with this calculation. Setting viewport and content margins to 0 hides the problem
    def _extra_margins(self) -> tuple[int, int]:
        m = self.contentsMargins()

        vm = self.viewportMargins()
        fw = self.frameWidth()

        sb_w = self.verticalScrollBar().sizeHint().width()
        sb_h = self.horizontalScrollBar().sizeHint().height()

        extra_w = m.left() + m.right() + vm.left() + vm.right() + fw * 2 + sb_w
        extra_h = m.top() + m.bottom() + vm.top() + vm.bottom() + fw * 2 + sb_h
        return extra_w, extra_h


class MessageBubble(MinimumSizeBrowser):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMouseTracking(True)


class InputChatBubble(MinimumSizeBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(False)
        self.document().setUndoRedoEnabled(True)
        self.setAcceptRichText(False)

class ChatMessageFrame(QFrame):
    """
    Stream-optimized message bubble.
    Key: coalesce many small chunks and re-render at most every ~50–75ms.
    """
    new_content = pyqtSignal()

    def __init__(self, role: str, md_buffer: str="", parent: QWidget = None):
        super().__init__(parent)
        self.role = role
        self._md_buffer = md_buffer
        self._build_ui()
        self._bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        # setup the copy button stuff (may move this to a helper later)
        self._copy_button.setText("Copy")
        self._copy_button.setVisible(False)
        self._copy_button.clicked.connect(lambda: QGuiApplication.clipboard().setText(self._md_buffer))

        self._bubble.installEventFilter(self)
        self.setMouseTracking(True)

        # Coalesced renderer
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_now)
        self._render_interval_ms = 200
        self._pending = False
        self._update_boundaries()
        self.start_render()

    def _build_ui(self):
        msg_frame_hbox = QHBoxLayout(self)  # layout self horizontally
        msg_frame_hbox.setContentsMargins(20, 20, 20, 20)
        msg_frame_hbox.setSpacing(20)

        # organizational widget to contain the components of a chat message bubble
        bubble = QWidget(self)

        # vertically layout the bubble
        bubble_vbox = QVBoxLayout(bubble)
        bubble_vbox.setContentsMargins(12, 12, 12, 12)
        bubble_vbox.setSpacing(12)

        # what goes inside the bubble (chat browser on top, actions below)
        browser = MessageBubble(bubble)
        actions_row = QWidget(bubble)

        actions_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed) # todo maybe consider the minimum height

        # horizontally layout the action row
        actions_row_hbox = QHBoxLayout(actions_row)
        actions_row_hbox.setContentsMargins(0, 0, 0, 0)
        actions_row_hbox.setSpacing(6)

        actions_row.setFixedHeight(65)

        # Actions
        copy_button = QToolButton(actions_row)

        # populate the action row
        actions_row_hbox.addWidget(HSpacer())
        actions_row_hbox.addWidget(copy_button)

        bubble_vbox.addWidget(browser)
        bubble_vbox.addWidget(actions_row)

        browser.setProperty("variant", self.role)

        if self.role.lower() == "user":
            msg_frame_hbox.addWidget(HSpacer(self))
            msg_frame_hbox.addWidget(bubble)
        else:
            msg_frame_hbox.addWidget(bubble)
            msg_frame_hbox.addWidget(HSpacer(self))

        self._bubble = bubble
        self._browser = browser
        self._copy_button = copy_button

    def append_markdown(self, chunk: str) -> None:
        self._md_buffer += chunk

    def start_render(self):
        if not self._render_timer.isActive():
            self._render_timer.start(self._render_interval_ms)

    def get_markdown(self) -> str:
        return self._md_buffer

    def set_markdown(self, text) -> None:
        self._md_buffer = text
        self.render_now()

    def stop_rendering(self) -> None:
        self._render_timer.stop()

    # --- internals -----------------------------------------------------
    def _render_now(self) -> None:
        # Avoid nested updates for smoother scrolling/layout
        self._browser.setUpdatesEnabled(False)
       # processed = self.preprocess_think_blocks(self._md_buffer)
        self._browser.setHtml(md.render(self._md_buffer))
        self._browser.setUpdatesEnabled(True)

    def _update_boundaries(self):                                                 #        ▲
        if self.parentWidget():                                                  # ▲      ▲
            w = int(self.parentWidget().width() * 0.75)                          # ▲ ▲   ▲ ▲
            h = int(float(w) * 0.618)                   # Follow the ratio       # ▲▲ ▲ ▲ ▲ ▲ ▲▲
            self._browser.setMaximumWidth(w)
            self._browser.setMaximumHeight(h)

    def _preprocess_think_blocks(self, text: str) -> str:
        return text.replace("<think>", "&lt;think&gt;").replace("</think>", "&lt;/think&gt;")

    # --- overrides -----------------------------------------------------
    def resizeEvent(self, event):
        self._update_boundaries()
        super().resizeEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self._copy_button.setVisible(True)
        if event.type() == QEvent.Leave:
            self._copy_button.setVisible(False)
        return super().eventFilter(obj, event)

class ChatInputBar(QWidget):
    userMsgSentSignal = pyqtSignal(str)
    stopRequested = pyqtSignal()
    clearRequested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.input_bubble = InputChatBubble(self)
        self._build_ui()
        self.send_btn.clicked.connect(self.send_btn_clicked)
        self.stop_btn.clicked.connect(self.stopRequested)
        self.clear_btn.clicked.connect(self.clearRequested)

    def _build_ui(self) -> None:
        self.send_btn = QPushButton("Send", self)
        self.stop_btn = QPushButton("Stop", self)
        self.clear_btn = QPushButton("Clear", self)
        rows = QVBoxLayout(self)
        rows.setContentsMargins(12, 12, 12, 12)
        rows.setSpacing(8)
        self.input_bubble.setPlaceholderText("Ask anything. Really.")
        self.input_bubble.installEventFilter(self)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(HSpacer())
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.send_btn)

        rows.addWidget(self.input_bubble)
        rows.addLayout(btn_row)

    def send_btn_clicked(self) -> None:
        text = self.input_bubble.toMarkdown()
        if text:
            self.userMsgSentSignal.emit(text)
            self.input_bubble.clear()

    def set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)

    # 'why': capture Enter vs Shift+Enter without stealing Tab navigation
    def eventFilter(self, obj, event):  # type: ignore[override]
        if obj is self.input_bubble and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                self.send_btn_clicked()
                return True
        return super().eventFilter(obj, event)

    def update_boundaries(self, w, h):
        cap_w = int(w * 0.65)
        cap_h = int(h * 0.45)
        # on the browser object, setting max width, and max height
        self.input_bubble.setMaximumWidth(cap_w)
        self.input_bubble.setMaximumHeight(cap_h)

        # setting minimum width. Don't need to state minimum height since layout manager does this
        min_w = int(w * 0.33)
        self.input_bubble.setMinimumWidth(min_w)
        self.setMinimumWidth(min_w)

        # on the widget itself
        self.setMaximumWidth(cap_w)
        self.setMaximumHeight(cap_h)

class TopBar(QWidget):
    modelChanged = pyqtSignal(str)
    settingsChanged = pyqtSignal(dict)
    newChatRequested = pyqtSignal()
    pickPersonalityRequested = pyqtSignal()
    createPersonalityRequested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)

        # Model selector
        self.model_combo = QComboBox(self)
        self.model_combo.setEditable(False)
        self.model_combo.setInsertPolicy(QComboBox.NoInsert)
        self.model_combo.addItems([
            "alpindale/WizardLM-2-8x22B",
            "zetasepic/Qwen2.5-72B-Instruct-abliterated",
            "zetasepic/Qwen2.5-72B-Instruct-abliterated-v2",
            "huihui-ai/Qwen2.5-72B-Instruct-abliterated",
            "huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated",
            "failspy/llama-3-70B-Instruct-abliterated",
            "failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5",
            "failspy/Llama-3-70B-Instruct-abliterated-v3",
            "failspy/Smaug-Llama-3-70B-Instruct-abliterated-v3",
            "crestf411/L3-70B-daybreak-abliterated-v0.4",
            "nvidia/Llama3-ChatQA-1.5-70B",
            "NousResearch/Hermes-2-Theta-Llama-3-70B",
            "m42-health/Llama3-Med42-70B",
            "Dogge/llama-3-70B-uncensored",
            "theo77186/Llama-3-70B-Instruct-norefusal",
            "KaraKaraWitch/Llama-3.3-MagicalGirl-2",
            "google/gemma-3-27b-it"
        ])
        self.model_combo.setCurrentIndex(0)

        self.model_combo.view().setMouseTracking(True)

        # Temperature only (Max tokens removed)
        self.temp_spin = QDoubleSpinBox(self)
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setDecimals(2)
        self.temp_spin.setMinimumWidth(140)

        # Action buttons
        self.new_chat_btn = QPushButton("New Chat", self)
        self.pick_persona_btn = QPushButton("Pick Personality", self)
        self.create_persona_btn = QPushButton("Create Personality", self)

        # Layout row
        layout.addWidget(QLabel("Model:"), 0, 0)
        layout.addWidget(self.model_combo, 0, 1)
        layout.addWidget(QLabel("Temperature:"), 0, 2)
        layout.addWidget(self.temp_spin, 0, 3)
        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 4)
        layout.addWidget(self.new_chat_btn, 0, 5)
        layout.addWidget(self.pick_persona_btn, 0, 6)
        layout.addWidget(self.create_persona_btn, 0, 7)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(4, 1)
        self._equalize_topbar_buttons()

        # Signals
        self.model_combo.currentTextChanged.connect(self.modelChanged.emit)
        self.temp_spin.valueChanged.connect(lambda _=None: self._emit_settings())
        self.new_chat_btn.clicked.connect(self.newChatRequested)
        self.pick_persona_btn.clicked.connect(self.pickPersonalityRequested)
        self.create_persona_btn.clicked.connect(self.createPersonalityRequested)

    def _emit_settings(self) -> None:
        self.settingsChanged.emit({"temperature": float(self.temp_spin.value())})

    def _equalize_topbar_buttons(self) -> None:
        btns = [self.new_chat_btn, self.pick_persona_btn, self.create_persona_btn]
        # Fix horizontal size so layout won't stretch them unevenly
        for b in btns:
            b.setSizePolicy(QSizePolicy.Fixed, b.sizePolicy().verticalPolicy())
        self.ensurePolished()  # ensures correct sizeHint with current style/font
        w = max(b.sizeHint().width() for b in btns)
        for b in btns:
            b.setFixedWidth(w + 100)


# ---- Scroll area to hold messages ----
class ChatScrollArea(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("chatScroll")
        # Important: let the viewport paint the stylesheet background
        self.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._container = QWidget()
        self._container.setObjectName("chatContent")
        # important: container should not claim to expand vertically
        self._container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self._chat_stack_layout = QVBoxLayout(self._container)
        self._chat_stack_layout.setContentsMargins(8, 8, 8, 8)
        self._chat_stack_layout.setSpacing(0)
        self._chat_stack_layout.addStretch(1)

        self.setWidget(self._container)

        # If this is a plain QWidget container, ensure the style engine paints its bg:
        self.setAttribute(Qt.WA_StyledBackground, True)

    def _append_bubble_to_stack(self, bubble: ChatMessageFrame) -> None:
        """
        Simply inserts a bubble at the bottom of the chat stack
        :param bubble:
        :return:
        """
        self.insert_bubble_at_idx(bubble, self._chat_stack_layout.count() - 1)

    def append_assistant_bubble_to_stack(self, text="") -> ChatMessageFrame:
        bubble = ChatMessageFrame(ChatRole.ASSISTANT, text)
        self._append_bubble_to_stack(bubble)
        bubble.start_render()
        return bubble

    def append_user_bubble_to_stack(self, text):
        bubble = ChatMessageFrame(ChatRole.USER, text)
        self._append_bubble_to_stack(bubble)
        return bubble

    def insert_bubble_at_idx(self, bubble: ChatMessageFrame, idx: int) -> None:
        """
        Inserts a bubble wherever you want, provided the idx is valid
        :param bubble:
        :param idx:
        :return:
        """
        bottom_of_stack = self._chat_stack_layout.count() - 1
        if idx > bottom_of_stack or idx < 0:
            print("wtf you doin bro? you cannot insert a bubble into oblivion")
            return None
        self._chat_stack_layout.insertWidget(idx, bubble)
        QTimer.singleShot(50, self.scroll_to_bottom)

    def peek_most_recent(self) -> ChatMessageFrame | None:
        idx = self._chat_stack_layout.count() - 2
        return self.get_frame_at_idx(idx)

    def get_frame_at_idx(self, idx) -> ChatMessageFrame | None:
        if idx >= 0:
            w = self._chat_stack_layout.itemAt(idx).widget()
        else:
            w = None
        return w

    def append_to_assistant(self, chunk) -> None:
        last_bubble = self.peek_most_recent()

        if isinstance(last_bubble, ChatMessageFrame) and last_bubble.role == ChatRole.ASSISTANT:
            chat_assistant_bubble = last_bubble
        else:
            chat_assistant_bubble = self.append_assistant_bubble_to_stack()

        chat_assistant_bubble.append_markdown(chunk)
        chat_assistant_bubble.start_render()

    def finish_assistant_stream(self):
        last_bubble = self.peek_most_recent()
        if isinstance(last_bubble, ChatMessageFrame) and last_bubble.role == ChatRole.ASSISTANT:
            last_bubble.stop_rendering()
            return last_bubble.get_markdown()
        else:
            print("Holy fuck. Tried to close down assistant stream and last bubble is not the assistant bubble.")
            return None

    def clear_messages(self) -> None:
        for i in reversed(range(self._chat_stack_layout.count() - 1)):
            item = self._chat_stack_layout.itemAt(i)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        QTimer.singleShot(0, self.scroll_to_bottom)

    def scroll_to_bottom(self) -> None:
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


# ---- Main Chat Window (View) ----
class ChatWindow(QMainWindow):
    # Outgoing (to Controller)
    sendMessage = pyqtSignal(str)
    stopRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    modelChanged = pyqtSignal(str)
    settingsChanged = pyqtSignal(dict)
    newChatRequested = pyqtSignal()
    pickPersonalityRequested = pyqtSignal()
    createPersonalityRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wild GPT")
        self.setWindowIcon(QIcon("wildAI.png"))
        self._build_ui()
        self.set_theme(ThemeManager.DARK)
        self.current_model = "deepseek-ai/DeepSeek-V3-0324"
        self.update_model(self.top_bar.model_combo.currentText())
        self.temperature = float(self.top_bar.temp_spin.value())

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("central")
        vbox = QVBoxLayout(central)  #maybe update to gridlayout?
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
       # central.setStyleSheet("border: 1px dashed red;") #uncomment for layout debugging!

        self.top_bar = TopBar(self)
        self.top_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.top_bar.setMaximumHeight(100)
        self.chat_stack = ChatScrollArea(self)
        self.input_bar = ChatInputBar(self)
        self.input_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # if you still want the input bar horizontally centered, wrap it
        self.input_pane = QWidget(self)
        self.input_pane.setObjectName("inputPane")
        hbox = QHBoxLayout(self.input_pane)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        self.input_pane.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hbox.addWidget(self.input_bar, 0, alignment=Qt.AlignHCenter)


        # --- assemble main layout ---
        vbox.addWidget(self.top_bar)
        vbox.addWidget(self.chat_stack)
        vbox.addWidget(self.input_pane)
        self.setCentralWidget(central)

        self.input_bar.userMsgSentSignal.connect(self.sendMessage)
        self.input_bar.stopRequested.connect(self.stopRequested)
        self.input_bar.clearRequested.connect(self.clearRequested)
        self.top_bar.modelChanged.connect(self.update_model)
        self.top_bar.settingsChanged.connect(self.settingsChanged)
        self.settingsChanged.connect(self.update_settings)

    # -------- Public slots --------
    def add_user_message(self, text: str) -> None:
        self.chat_stack.append_user_bubble_to_stack(text)

    def append_assistant_stream(self, chunk) -> None:
        self.chat_stack.append_to_assistant(chunk)

    def finish_assistant_stream(self) -> str:
        return self.chat_stack.finish_assistant_stream()

    def set_busy(self, busy: bool) -> None:
         self.input_bar.set_busy(busy)

    def set_theme(self, theme: Theme) -> None:
        """Public API to switch theme at runtime."""
        if theme is not None:
            ThemeManager.apply_palette(QApplication.instance(), theme)  # type: ignore[arg-type]
            self.setStyleSheet(ThemeManager.stylesheet(theme))

    def on_clear_clicked(self) -> None:
        self.chat_stack.clear_messages()

    def update_model(self, new_model):
        self.current_model = str(new_model)

    def update_settings(self, new_settings: dict) -> None:
        for setting_name, value in new_settings.items():
            if setting_name == "temperature":
                self.temperature = value

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.input_bar.update_boundaries(self.width(), self.height())
