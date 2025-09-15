from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer, QEvent, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QFontMetricsF, QTextOption, QGuiApplication, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpacerItem, QWidget, QTextBrowser, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QToolButton,
)
from markdown_it import MarkdownIt

# markdown parser is stateless and shared
md = MarkdownIt()

# ---- Light-weight role identifiers (kept here for typing only; real model lives elsewhere) ----
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
        button_bg_pressed="#191e2a",
        button_border="#2a3142",
        accent1="#3857ff",
        accent2="#3a5fff",
        selection="#2a3553",
        user_bubble_bg="qlineargradient( x1:0, y1:0, x2:1, y2:1, stop:0 #7d5fff, stop:1 #9c27b0 )",
        assistant_bubble_bg="rgba(18, 21, 33, 0.6);",
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
        QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QLineEdit {{
            background: {theme.input_bg};
            color: {theme.text};
            border: 3px solid {theme.border};
            border-radius: {theme.widget_radius}px;
            padding: {theme.widget_padding}px {theme.widget_padding}px;
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
            border: {theme.button_border};
            border-radius: 6px;
            padding: {theme.widget_padding}px {theme.widget_padding}px;
        }}

        QPushButton:hover, QToolButton:hover {{
            background: {theme.button_bg_hover};
        }}
        
        QPushButton:pressed, QToolButton:pressed {{
            background: {theme.button_bg_pressed}; /* Or define a separate click color in Theme if desired */
        }}
        QPushButton:disabled {{ color: #8b93a6; }}

        /* User bubble: ChatGPT style */
        #bubbleFrame[variant="user"] {{
            background: {theme.user_bubble_bg};
            color: {theme.text};
            border-radius: 30px;
            border: 3px solid {theme.border};
        }}
        /* Assistant bubble: ChatGPT style */
        #bubbleFrame[variant="assistant"] {{
            background: {theme.assistant_bubble_bg};
            color: {theme.text};
            border-radius: 50px;
            border: 1px solid {theme.border};
        }}
        
        QTextBrowser#bubbleFrame {{
            font-family: Inter, Segoe UI, Roboto, Arial;
            font-size: 30px;
            color: #eaeef2;
        }}
        
        #chatViewport {{ background: {theme.bg}; }}
        """


class HSpacer(QWidget):
    """
    Horizontal spacer that can be used to help align widgets
    """
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
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setFrameStyle(QFrame.NoFrame)

        # these help center the text browser and add some padding
        inset = 0  # your bubble’s inner padding
        offset = 20
        self.setViewportMargins(inset + offset, inset + offset, inset, inset)  # left top right bottom

        # We resize instead of scrolling.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Recompute geometry whenever the document changes.
        self.document().documentLayout().documentSizeChanged.connect(self.updateGeometry)

        self.setObjectName("bubbleFrame")
        self._sync_doc()

    # --- qt overrides -------------------------------------------------
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

    def changeEvent(self, e):
        if e.type() in (
            QEvent.FontChange,
            QEvent.StyleChange,
            QEvent.ApplicationFontChange,
            QEvent.LayoutDirectionChange,
        ):
            self._sync_doc()
            self.updateGeometry()
        super().changeEvent(e)

    def resizeEvent(self, e) -> None:  # type: ignore[override]
        super().resizeEvent(e)
        # Ensure layout reacts when the widget is resized by its parent.
        self.updateGeometry()

    # --- utilities ------------------------------------------------------
    def _extra_margins(self) -> tuple[int, int]:
        """
        Everything around the QTextDocument contents: widget contents margins,
        frame width, and the QAbstractScrollArea viewport margins.
        """
        m = self.contentsMargins()
        vm = self.viewportMargins()          # <-- you were not counting these
        fw = self.frameWidth()
        extra_w = m.left() + m.right() + vm.left() + vm.right() + 2 * fw
        extra_h = m.top() + m.bottom() + vm.top() + vm.bottom() + 2 * fw
        return extra_w, extra_h

    def _sync_doc(self):
        doc = self.document()
        # 1) Keep document font = widget font
        if doc.defaultFont() != self.font():
            doc.setDefaultFont(self.font())

        # 2) Keep text options consistent with the widget
        opt = doc.defaultTextOption()
        changed = False
        if opt.wrapMode() != self.wordWrapMode():
            opt.setWrapMode(self.wordWrapMode())
            changed = True
        # Optional but helpful: consistent tabs with current font
        desired_tabs = QFontMetricsF(self.font()).horizontalAdvance(' ') * 4
        if abs(opt.tabStopDistance() - desired_tabs) > 0.5:
            opt.setTabStopDistance(desired_tabs)
            changed = True
        if changed:
            doc.setDefaultTextOption(opt)

class inputBarBrowser(ChatTextBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(False)
        inset = 0  # your bubble’s inner padding
        offset = 0
        self.setViewportMargins(inset , inset, inset, inset + offset)  # left top right bottom

    def heightForWidth(self, w: int) -> int:
        parent_h = super().heightForWidth(w)
        return parent_h + 15


class ChatMessageBubble(QFrame):
    """
    The main message bubble class!
    The ChatMessageBubble is a widget, horizontally laid out, which contains a spacer and the message bubble.
    The message bubble is a widget that stacks the chat label, the message itself, and the actions row.
    The messsage is actually a custom QTextBrowser which allows the type of resizing you would expect
    from an AI chat bubble.
    """
    new_content = pyqtSignal()  # this is a signal that fires when new markdown content is available to display
    def __init__(self, role: str, md_buffer: str, parent: QWidget = None):
        super().__init__(parent)
        self.role = role
        self._md_buffer = md_buffer
        self._build_ui()
        self._bubble.installEventFilter(self)
        self._bubble.setMouseTracking(True)
        self.setMouseTracking(True)
        self.new_content.connect(self.new_markdown_available)

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
        browser.setHtml(md.render(self._md_buffer))

        # Actions row layout for actions like copy
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(6)

        # Actions
        copy_button = QToolButton()
        copy_button.setText("Copy")
        copy_button.setVisible(False)

        copy_button.clicked.connect(lambda: QGuiApplication.clipboard().setText(self._md_buffer))

        # add widgets to the layout
        actions_row.addWidget(HSpacer())
        actions_row.addWidget(copy_button)

        actions_container = QWidget()
        actions_container.setLayout(actions_row)
        actions_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        actions_container.setMinimumHeight(copy_button.sizeHint().height())

        # add components to the frame
        msg_layout_vbox.addWidget(browser)
        msg_layout_vbox.addWidget(actions_container)

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
        self._copy_button = copy_button

    def resizeEvent(self, event):
        """Ensure bubbles max width = 85% of parent width."""
        if self.parentWidget():
            cap = int(self.parentWidget().width() * 0.85)
            self._bubble.setMaximumWidth(cap)
        super().resizeEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self._copy_button.setVisible(True)

        if event.type() == QEvent.Leave:
            self._copy_button.setVisible(False)
        return super().eventFilter(obj, event)

    def append_markdown(self, chunk: str) -> None:
        """Append a markdown chunk to the buffer."""
        self._md_buffer += chunk
        self.new_content.emit()

    def get_markdown(self) -> str:
        """Return the raw markdown buffer."""
        return self._md_buffer

    def new_markdown_available(self):
        self._browser.setHtml(md.render(self._md_buffer))
        self.updateGeometry()


# ---- Scroll area to hold messages ----
class ChatScrollArea(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.viewport().setObjectName("chatViewport")
        self._container = QWidget()
        self._chat_stack_layout = QVBoxLayout(self._container)
        self._chat_stack_layout.setContentsMargins(12, 12, 12, 12)
        self._chat_stack_layout.setSpacing(6)
        self._tail_spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self._chat_stack_layout.addItem(self._tail_spacer)
        self.setWidget(self._container)

    def add_bubble(self, bubble: ChatMessageBubble) -> None:
        self._chat_stack_layout.insertWidget(self._chat_stack_layout.count() - 1, bubble)
        QTimer.singleShot(0, self._after_layout_change)

    def peek_most_recent(self) -> ChatMessageBubble | None:
        idx = self._chat_stack_layout.count() - 2
        w = self._chat_stack_layout.itemAt(idx).widget() if idx >= 0 else None
        return w


    def scroll_to_bottom(self) -> None:
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_messages(self) -> None:
        # Remove all except the final stretch
        for i in reversed(range(self._chat_stack_layout.count() - 1)):
            item = self._chat_stack_layout.itemAt(i)
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
        content_h = self._chat_stack_layout.sizeHint().height()
        vp_h = self.viewport().height()
        vpol = QSizePolicy.Expanding if content_h < vp_h else QSizePolicy.Minimum
        self._tail_spacer.changeSize(0, 0, QSizePolicy.Minimum, vpol)
        self._chat_stack_layout.invalidate()
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
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setMinimumHeight()

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

# ---- Input bar ----
class ChatInputBar(QWidget):
    # ChatInputBar signals
    userMsgSentSignal = pyqtSignal(str)
    stopRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # UI elements
        self.input_bar = inputBarBrowser()
        self.send_btn = QPushButton("Send", self)
        self.stop_btn = QPushButton("Stop", self)
        self.clear_btn = QPushButton("Clear", self)
        # build the layout
        self._build_ui()
        # connect our signals and slots
        self.send_btn.clicked.connect(self.send_btn_clicked)
        self.stop_btn.clicked.connect(self.stopRequested)
        self.clear_btn.clicked.connect(self.clearRequested)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.input_bar.setPlaceholderText("Ask anything")
        self.input_bar.setAcceptRichText(False)
        self.input_bar.installEventFilter(self)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.stop_btn.setEnabled(False)

        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(HSpacer())
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.send_btn)

        self.btn_container = QWidget()
        self.btn_container.setLayout(btn_row)
        layout.addWidget(self.input_bar)
        layout.addWidget(self.btn_container)

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

    def resizeEvent(self, event):
        """Ensure bubbles max width = 85% of parent width."""
        if self.parentWidget():
            cap = int(self.parentWidget().width() * 0.5)
            self.input_bar.setMaximumWidth(cap)
            self.input_bar.setMinimumWidth(cap)
        super().resizeEvent(event)


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
            "alpindale/WizardLM-2-8x22B",
            "zetasepic/Qwen2.5-72B-Instruct-abliterated",
            "zetasepic/Qwen2.5-72B-Instruct-abliterated-v2",
            "huihui-ai/Qwen2.5-72B-Instruct-abliterated",
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
            "KaraKaraWitch/Llama-3.3-MagicalGirl-2"
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
        self.setWindowIcon(QIcon("wildAI.ico"))
        #components
        self.topbar = TopBar(self)
        self.chat_stack = ChatScrollArea(self)
        self.input_bar = ChatInputBar(self)
        # Typing indicator bubble (hidden when idle)
        self.busy_indicator = QLabel("…", self)
        #get to building...
        self._build_ui()
        self.set_theme(ThemeManager.DARK)
        self.current_model = "deepseek-ai/DeepSeek-V3-0324"
        self.update_model(self.topbar.model_combo.currentText())
        self.temperature = float(self.topbar.temp_spin.value())

    def _build_ui(self) -> None:
        central = QWidget(self)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self.topbar)
        vbox.addWidget(self.chat_stack, 1)
        vbox.addWidget(self.input_bar, 0, Qt.AlignHCenter)
        self.setCentralWidget(central)

        # Wire outward
        self.input_bar.userMsgSentSignal.connect(self.sendMessage)
        self.input_bar.stopRequested.connect(self.stopRequested)
        self.input_bar.clearRequested.connect(self.clearRequested)
        self.topbar.modelChanged.connect(self.update_model)
        self.modelChanged.connect(self.update_model)
        self.topbar.settingsChanged.connect(self.settingsChanged)
        self.settingsChanged.connect(self.update_settings)

        self.busy_indicator.setAlignment(Qt.AlignLeft)
        self.busy_indicator.setStyleSheet("color:#888; padding:6px 10px;")
        self.busy_indicator.hide()

    # -------- Public slots for Controller to manipulate the View --------
    def add_user_message(self, text: str) -> None:
        self.chat_stack.add_bubble(ChatMessageBubble(ChatRole.USER, text))

    def add_assistant_message(self, text: str) -> None:
        self.chat_stack.add_bubble(ChatMessageBubble(ChatRole.ASSISTANT, text))

    def finish_assistant_stream(self) -> None:
        pass

    def set_busy(self, busy: bool) -> None:
        self.input_bar.set_busy(busy)

    def set_theme(self, theme: Theme) -> None:
        """Public API to switch theme at runtime."""
        if theme is not None:
            ThemeManager.apply_palette(QApplication.instance(), theme)  # type: ignore[arg-type]
            self.setStyleSheet(ThemeManager.stylesheet(theme))

    def clear_messages(self) -> None:
        self.chat_stack.clear_messages()

    # busy indicator seems insane! We could just make the indicator visible/hidden rather than inserting and removing
    # it's also very boring just ... that don't even move

    # -------- Internal handlers --------

    def on_clear_clicked(self) -> None:
        self.clear_messages()

    def update_model(self, new_model):
        self.current_model = str(new_model)

    def update_settings(self, new_settings: dict) -> None:
        for setting_name, value in new_settings.items():
            if setting_name == "temperature":
                self.temperature = value
