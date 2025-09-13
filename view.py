# file: ui/chat_view.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer, QEvent, pyqtSignal, QSize, QSizeF
from PyQt5.QtGui import QFont, QPalette, QColor, QFontMetricsF, QTextDocument, QTextOption
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpacerItem, QWidget, QTextBrowser, QFrame, QHBoxLayout, QVBoxLayout, QLabel,
)

from typing import Iterable, List


# ---- Light-weight role identifiers (kept here for typing only; real model lives elsewhere) ----
@dataclass(frozen=True)
class ChatRole:
    USER: str = "user"
    ASSISTANT: str = "assistant"
    SYSTEM: str = "system"


# ---- Utilities ----
import html
import re

# Regex for fenced code blocks: ```lang\n ... \n```
_MD_CODEBLOCK_RE = re.compile(r"```(\w+)?\\n([\\s\\S]*?)```", re.MULTILINE)
# Regex for inline code: `code`
_MD_INLINE_CODE_RE = re.compile(r"`([^`]+)`")

def _markdown_to_html(text: str) -> str:
    """
    Convert a small subset of Markdown to safe HTML for QLabel.
    Supports:
    - Triple backtick code blocks → <pre>
    - Inline code → <code>
    - Escapes all other HTML
    - Preserves newlines
    """
    # Escape, but keep quotes as-is
    escaped = html.escape(text, quote=False)

    # Replace fenced code blocks
    def block_repl(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = html.escape(m.group(2))  # escape inside code too
        return (
            "<pre style='font-family: Consolas, Menlo, monospace; "
            "white-space: pre-wrap; margin:6px 0; padding:8px; "
            "border-radius:10px; background:#1112; border:1px solid #0001;'>"
            f"{code}</pre>"
        )

    html_text = _MD_CODEBLOCK_RE.sub(block_repl, escaped)

    # Replace inline code spans
    def inline_repl(m: re.Match) -> str:
        code = html.escape(m.group(1))
        return (
            f"<code style='font-family: Consolas, Menlo, monospace; "
            f"background:#1112; border-radius:4px; padding:2px 4px;'>"
            f"{code}</code>"
        )

    html_text = _MD_INLINE_CODE_RE.sub(inline_repl, html_text)

    # Replace line breaks with <br>
    html_text = html_text.replace("\\n", "<br>")

    return html_text


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
    button_border: str
    accent1: str
    accent2: str
    selection: str
    user_bubble_grad0: str
    user_bubble_grad1: str
    user_bubble_border: str
    assistant_bubble_bg: str
    assistant_bubble_border: str


class ThemeManager:
    DARK = Theme(
        name="Dark",
        font_family="Inter, Segoe UI, Roboto, Arial",
        font_size=25,
        widget_padding=10,
        widget_radius=20,
        bg="#0f1115",
        text="#eaeef2",
        panel="#121521",
        border="#20263a",
        input_bg="#151922",
        button_bg="#1d2433",
        button_bg_hover="#252d40",
        button_border="#2a3142",
        accent1="#3857ff",
        accent2="#3a5fff",
        selection="#2a3553",
        user_bubble_grad0="#3857ff22",
        user_bubble_grad1="#3857ff33",
        user_bubble_border="#3a5fff55",
        assistant_bubble_bg="#121521",
        assistant_bubble_border="#20263a",
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
        button_border="#d9deea",
        accent1="#335cff",
        accent2="#2a50f8",
        selection="#dbe4ff",
        user_bubble_grad0="#335cff11",
        user_bubble_grad1="#335cff22",
        user_bubble_border="#335cff44",
        assistant_bubble_bg="#f7f8fb",
        assistant_bubble_border="#e7ebf3",
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
        QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QLineEdit {{
            background: {theme.input_bg};
            color: {theme.text};
            border: 3px solid {theme.border};
            border-radius: {theme.widget_radius}px;
            padding: {theme.widget_padding}px;
        }}
        QPushButton {{
            background: {theme.button_bg};
            color: {theme.text};
            border: 1px solid {theme.button_border};
            border-radius: {theme.widget_radius}px;
            padding: {theme.widget_padding}px {theme.widget_padding}px;
        }}
        QToolButton {{
            background: rgba(18, 21, 33, 0.6); /* 60% opaque dark */;;
            color: {theme.text};
            border: 1px solid {theme.button_border};
            border-radius: {theme.widget_radius}px;
            padding-bottom: 5px;
        }}
        QPushButton:hover, QToolButton:hover {{ background: {theme.button_bg_hover}; }}
        QPushButton:disabled {{ color: #8b93a6; }}

        /* User bubble: ChatGPT style */
        #bubbleFrame[variant="user"] {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #7d5fff,
                stop:1 #9c27b0 );
            color: #ffffff;
            border-radius: 30px;
            border: 3px solid {theme.border};
        }}
        /* Assistant bubble: ChatGPT style */
        #bubbleFrame[variant="assistant"] {{
            background: rgba(18, 21, 33, 0.6); /* 60% opaque dark */;
            color: {theme.text};
            border-radius: 50px;
            border: 1px solid {theme.border};
        }}
        #bubbleLabel {{
            selection-background-color: {theme.selection};
        }}
        #chatViewport {{ background: {theme.bg}; }}
        """


class HSpacer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # don’t block clicks
        self.setStyleSheet("background: transparent; border: none;")

class ChatTextBrowser(QTextBrowser):
    """
    QTextBrowser that reports a size hint just large enough to fit its text
    without wrapping (up to the widget's maximum width). Once the layout
    constrains its width below that ideal, the widget wraps text and grows
    vertically using height-for-width so that no scrollbars are needed.

    Key points:
      - sizeHint(): returns the minimal width that fits content in-place
        (no wrapping), capped by maximumWidth(). Height is computed for that
        width via heightForWidth().
      - hasHeightForWidth()/heightForWidth(): provide a correct height for
        any constrained width by temporarily shaping the QTextDocument to the
        given width. This allows layouts to vertically expand the widget as it
        gets narrower.
      - Scrollbars are disabled; the widget is expected to resize instead.

    Works best when placed in a QLayout that respects height-for-width.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Wrap to the widget width when constrained by the layout.
        self.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

        # Prefer expanding horizontally until hitting max width; grow vertically as needed.
        sp = self.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        sp.setVerticalPolicy(QSizePolicy.Policy.Minimum)
        self.setSizePolicy(sp)

        # We resize instead of scrolling.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Recompute geometry whenever the document changes.
        self.document().documentLayout().documentSizeChanged.connect(self._on_doc_size_changed)
        self.document().contentsChanged.connect(self._on_doc_size_changed)

        self.setObjectName("bubbleFrame")

    # --- sizing helpers -------------------------------------------------
    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, w: int) -> int:  # type: ignore[override]
        if w <= 0:
            return super().height()
        extra_w, extra_h = self._extra_margins()
        content_w = max(0, w - extra_w)
        doc = self.document()
        old_tw = doc.textWidth()
        try:
            doc.setTextWidth(content_w)
            doc_h = math.ceil(doc.size().height())
        finally:
            doc.setTextWidth(old_tw)
        return int(doc_h + extra_h)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        extra_w, _ = self._extra_margins()
        doc = self.document()

        # Compute the ideal *unconstrained* content width (no wrapping).
        old_tw = doc.textWidth()
        try:
            doc.setTextWidth(-1)  # "unbounded"; lets idealWidth reflect natural width
            ideal_content_w = math.ceil(doc.idealWidth())
        finally:
            doc.setTextWidth(old_tw)

        # Target width = natural content width + chrome, but don't exceed max.
        w = int(ideal_content_w + extra_w)
        w = min(w, self.maximumWidth())
        return QSize(w, self.heightForWidth(w))

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        # For this widget, the minimum usable size equals the natural hint.
        return self.sizeHint()

    # --- event hooks ----------------------------------------------------
    def _on_doc_size_changed(self, *_) -> None:
        # Trigger the parent layout to recalculate using updated hints.
        self.updateGeometry()

    def resizeEvent(self, e) -> None:  # type: ignore[override]
        super().resizeEvent(e)
        # Ensure layout reacts when the widget is resized by its parent.
        self.updateGeometry()

    # --- utilities ------------------------------------------------------
    def _extra_margins(self) -> tuple[int, int]:
        m = self.contentsMargins()
        fw = self.frameWidth()
        extra_w = m.left() + m.right() + 2 * fw
        extra_h = m.top() + m.bottom() + 2 * fw
        return extra_w, extra_h

class ChatMessageBubble(QFrame):
    def __init__(self, role: str, text: str, parent: QWidget = None):
        super().__init__(parent)
        self.role = role
        self.text = text
        self._build_ui()

    def _build_ui(self):
        # Outer horizontal layout for left/right alignment
        msg_row = QHBoxLayout(self)
        msg_row.setContentsMargins(8, 4, 8, 4)
        msg_row.setSpacing(8)

        # organizational widget to contain the components of a chat message bubble
        bubble = QWidget()
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        bubble.setMinimumHeight(5)

        # vertical layout to put inside the bubble.
        msg_layout_vbox = QVBoxLayout(bubble)
        msg_layout_vbox.setContentsMargins(12, 10, 12, 10)
        msg_layout_vbox.setSpacing(0)

        # Text content
        browser = ChatTextBrowser()
        browser.setHtml(_markdown_to_html(self.text))  # in real app, convert Markdown → HTML first

        # add components to the frame
        msg_layout_vbox.addWidget(browser)

        # message bubble is complete. align it right if user or left if assistant

        browser.setProperty("variant", self.role)

        if self.role.lower() == "user":
            msg_row.addWidget(HSpacer())
            msg_row.addWidget(bubble)
        else:
            msg_row.addWidget(bubble)
            msg_row.addWidget(HSpacer())

        # Keep reference for resizing
        self._bubble = bubble
        self._browser = browser

    def resizeEvent(self, event):
        """Ensure bubbles max width = 85% of parent width."""
        if self.parentWidget():
            cap = int(self.parentWidget().width() * 0.85)
            print(f"the cap is {cap}")
            self._bubble.setMaximumWidth(cap)
        super().resizeEvent(event)

# ---- Scroll area to hold messages ----
class ChatScrollArea(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.viewport().setObjectName("chatViewport")

        self._container = QWidget()
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(12, 12, 12, 12)
        self._vbox.setSpacing(6)
        self._tail_spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self._vbox.addItem(self._tail_spacer)
        self.setWidget(self._container)

    # Replace add_bubble with:
    def add_bubble(self, bubble: ChatMessageBubble) -> None:
        self._vbox.insertWidget(self._vbox.count() - 1, bubble)
        # apply current cap after insertion + layout pass
        QTimer.singleShot(0, self._after_layout_change)

    def scroll_to_bottom(self) -> None:
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_messages(self) -> None:
        # Remove all except the final stretch
        for i in reversed(range(self._vbox.count() - 1)):
            item = self._vbox.itemAt(i)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        QTimer.singleShot(0, self._after_layout_change)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Recompute tail spacer expansion to prevent scrollable blank space
        self._update_tail_spacer()

    def _after_layout_change(self) -> None:
        self._update_tail_spacer()
        self.scroll_to_bottom()

    def _update_tail_spacer(self) -> None:
        # Expand the tail spacer only when content is shorter than the viewport
        content_h = self._vbox.sizeHint().height()
        vp_h = self.viewport().height()
        vpol = QSizePolicy.Expanding if content_h < vp_h else QSizePolicy.Minimum
        self._tail_spacer.changeSize(0, 0, QSizePolicy.Minimum, vpol)
        self._vbox.invalidate()
        self._container.updateGeometry()


# --- Drop-in: auto-growing text edit for the chat input bar ---
import math
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit, QSizePolicy

class AutoGrowTextEdit(QTextEdit):
    """
    Grows vertically as the user types, between min_rows and max_rows.
    Keeps scrollbars hidden until max_rows is reached.
    """
    def __init__(self, parent=None, min_rows: int = 2, max_rows: int = 8):
        super().__init__(parent)
        self._min_rows = max(1, min_rows)
        self._max_rows = max(self._min_rows, max_rows)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self.textChanged.connect(self._update_height)

        # Initial sizing
        self._update_height()

    def _row_px(self) -> int:
        # Use lineSpacing for better cross-font results
        return self.fontMetrics().lineSpacing()

    def _frame_and_margins(self) -> int:
        # Sum frame + contents + document margins (top+bottom)
        fw = self.frameWidth() * 2
        cm = self.contentsMargins().top() + self.contentsMargins().bottom()
        dm = int(self.document().documentMargin()) * 2
        return fw + cm + dm

    def _rows_to_height(self, rows: int) -> int:
        return rows * self._row_px() + self._frame_and_margins()

    def _doc_height(self) -> int:
        # Ensure layout knows current width
        self.document().setTextWidth(self.viewport().width())
        size = self.document().documentLayout().documentSize()
        return math.ceil(size.height()) + self._frame_and_margins()

    def _update_height(self) -> None:
        min_h = self._rows_to_height(self._min_rows)
        max_h = self._rows_to_height(self._max_rows)
        doc_h = self._doc_height()

        new_h = max(min_h, min(max_h, doc_h))
        self.setMinimumHeight(min_h)
        self.setMaximumHeight(max_h)
        # Fix height only when below max to avoid fighting scrollbar behavior
        if doc_h < max_h:
            self.setFixedHeight(new_h)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            # At/above max rows: allow scrolling
            self.setFixedHeight(max_h)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Reflow on width changes (e.g., window resize/theme change)
        self._update_height()

# ---- Input bar ----
class ChatInputBar(QWidget):
    # ChatInputBar signals
    userMsgSentSignal = pyqtSignal(str)
    stopRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # UI elements
        self.input_bar = AutoGrowTextEdit(self, min_rows=1, max_rows=16)
        self.send_btn = QPushButton("Send", self)
        self.stop_btn = QPushButton("Stop", self)
        self.clear_btn = QPushButton("Clear", self)
        # build the layout
        self._build_ui()
        # connect our signals and slots
        self.send_btn.clicked.connect(self.send_btn_clicked)
        self.stop_btn.clicked.connect(self.stopRequested)
        self.clear_btn.clicked.connect(self.clearRequested)
        self.setMinimumWidth(1200)
        self.setSizePolicy(QSizePolicy.Maximum, self.sizePolicy().verticalPolicy())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(8)
        self.input_bar.setPlaceholderText("Ask anything")
        self.input_bar.setMinimumHeight(120)
        self.input_bar.setMaximumHeight(600)
        self.input_bar.setAcceptRichText(False)
        self.input_bar.installEventFilter(self)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.stop_btn.setEnabled(False)

        btn_row.addWidget(self.clear_btn)
        btn_row.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.send_btn)

        layout.addWidget(self.input_bar)
        layout.addLayout(btn_row)

    def send_btn_clicked(self) -> None:
        text = self.input_bar.toPlainText().strip()
        if text:
            self.userMsgSentSignal.emit(text)
            self.input_bar.clear()

    def set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.input_bar.setReadOnly(busy)

    # 'why': capture Enter vs Shift+Enter without stealing Tab navigation
    def eventFilter(self, obj, event):  # type: ignore[override]
        if obj is self.input_bar and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                self.send_btn_clicked()
                return True
        return super().eventFilter(obj, event)


# -- REPLACE the entire TopBar class --
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
            "deepseek-ai/DeepSeek-V3-0324",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
        ])
        self.model_combo.setCurrentIndex(0)

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
        #components
        self.topbar = TopBar(self)
        self.chat = ChatScrollArea(self)
        self.input = ChatInputBar(self)
        # Typing indicator bubble (hidden when idle)
        self._typing_lbl = QLabel("…", self)
        #get to building...
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        central = QWidget(self)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self.topbar)
        vbox.addWidget(self.chat, 1)
        vbox.addWidget(self.input, 0, Qt.AlignHCenter)
        self.setCentralWidget(central)

        # Wire outward
        self.input.userMsgSentSignal.connect(self.sendMessage)
        self.input.stopRequested.connect(self.stopRequested)
        self.input.clearRequested.connect(self._on_clear_clicked)
        self.topbar.modelChanged.connect(self.modelChanged)
        self.topbar.settingsChanged.connect(self.settingsChanged)

        self._typing_lbl.setAlignment(Qt.AlignLeft)
        self._typing_lbl.setStyleSheet("color:#888; padding:6px 10px;")
        self._typing_lbl.hide()

    # -------- Public slots for Controller to manipulate the View --------
    def add_user_message(self, text: str) -> None:
        self.chat.add_bubble(ChatMessageBubble(ChatRole.USER, text))

    def add_assistant_message(self, text: str) -> None:
        self.chat.add_bubble(ChatMessageBubble(ChatRole.ASSISTANT, text))

    # redesign
    def append_assistant_stream(self, chunk: str) -> None:
        # 'why': efficient streaming—update the last assistant bubble when possible
        # If last is assistant, append; else create one
        vbox = self.chat._vbox
        idx = vbox.count() - 2  # before the stretch
        target: Optional[ChatMessageBubble] = None
        if idx >= 0:
            w = vbox.itemAt(idx).widget()
            if isinstance(w, ChatMessageBubble) and w.role == ChatRole.ASSISTANT:
                target = w
        if target is None:
            target = ChatMessageBubble(ChatRole.ASSISTANT, "")
            self.chat.add_bubble(target)
        # Find label and extend html
        lbl: QLabel = target.findChild(QLabel, "bubbleLabel")  # type: ignore[assignment]
        prev = lbl.text()
        # Avoid double-escaping by converting chunk only and concatenating
        lbl.setText(prev + _markdown_to_html(chunk))
        QTimer.singleShot(0, self.chat.scroll_to_bottom)

    def finish_assistant_stream(self) -> None:
        self._set_typing(False)

    def set_busy(self, busy: bool) -> None:
        self.input.set_busy(busy)
        self._set_typing(busy)

    def set_theme(self, theme: Theme) -> None:
        """Public API to switch theme at runtime."""
        ThemeManager.apply_palette(QApplication.instance(), theme)  # type: ignore[arg-type]
        self.setStyleSheet(ThemeManager.stylesheet(theme))

    def clear_messages(self) -> None:
        self.chat.clear_messages()

    # -------- Internal handlers --------
    def _set_typing(self, typing: bool) -> None:
        if typing and self._typing_lbl.isHidden():
            self._typing_lbl.show()
            self.chat._vbox.insertWidget(self.chat._vbox.count() - 1, self._typing_lbl)
        elif not typing and not self._typing_lbl.isHidden():
            self._typing_lbl.hide()
            self._typing_lbl.setParent(None)

    def _on_clear_clicked(self) -> None:
        self.clear_messages()
        self.clearRequested.emit()

    # -------- Styling --------
    def _apply_style(self) -> None:
        theme = ThemeManager.DARK
        ThemeManager.apply_palette(QApplication.instance(), theme)  # type: ignore[arg-type]
        self.setStyleSheet(ThemeManager.stylesheet(theme))