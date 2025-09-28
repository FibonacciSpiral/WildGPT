from __future__ import annotations

from PyQt5.QtCore import QTimer, QEvent, pyqtSignal, Qt, QSize
from PyQt5.QtGui import QColor, QGuiApplication, QTextCursor, QTextDocument, \
    QPainter
from PyQt5.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QToolButton,
    QSizePolicy
)
from markdown_it import MarkdownIt

from src.minimum_size_browser import MessageBubble

# Markdown parser is stateless and shared
md = MarkdownIt()
md = md.disable(["html_block", "html_inline"])

class HSpacer(QWidget):
    """
    Horizontal spacer that can be used to help align widgets
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # todo make sure this is okay
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # don’t block clicks
        self.setStyleSheet("background: transparent; border: none;")

class TypingIndicator(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.dot_count = 3
        self.current_frame = 0
        self.dot_radius = 26
        self.spacing = 50
        self.color = QColor(255, 255, 255, int(0.5 * 255))
        self.timer = QTimer(self)
        QTimer.singleShot(10, self.update_frame)

        self.setMinimumSize(self.spacing * (self.dot_count-1) + self.dot_radius * self.dot_count + 15, self.dot_radius + self.spacing * 2)

    def update_frame(self):
        if self.current_frame >= self.dot_count:
            QTimer.singleShot(200, self.update_frame)
        else:
            QTimer.singleShot(75, self.update_frame)

        self.update()  # triggers paintEvent


    def paintEvent(self, event):
        painter = QPainter(self)
        center_y = self.height() // 2
        total_width = (self.dot_count - 1) * self.spacing + self.dot_radius
        start_x = (self.width() - total_width) // 2

        for i in range(self.dot_count):
            x = start_x + i * self.spacing
            offset = -20 if i == self.current_frame else 0  # bounce effect
            painter.setBrush(self.color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                x - self.dot_radius // 2,
                center_y + offset - self.dot_radius // 2,
                self.dot_radius,
                self.dot_radius
            )
        self.current_frame += 1
        if self.current_frame > self.dot_count:
            self.current_frame = 0

class MessageFrame(QFrame):
    size_changed = pyqtSignal(QSize)
    def __init__(self, role: str, parent: QWidget = None):
        super().__init__(parent)
        self.role = role
        # todo make the progress bubble look nicer.

class ProgressIndicator(MessageFrame):
    def __init__(self, role: str, parent: QWidget = None):
        super().__init__(role, parent)
        msg_frame_hbox = QHBoxLayout(self)  # layout self horizontally
        msg_frame_hbox.setContentsMargins(20, 20, 20, 20)
        msg_frame_hbox.setSpacing(20)
        msg_frame_hbox.addWidget(TypingIndicator(self))
        msg_frame_hbox.addWidget(HSpacer(self))

    def update_boundaries(self, parent_w):
        pass


class ChatMessageFrame(MessageFrame):
    """
    Stream-optimized message bubble.
    """
    new_content = pyqtSignal()

    def __init__(self, role: str, md_buffer: str="", parent: QWidget = None):
        super().__init__(role, parent)
        self._md_buffer = md_buffer
        self._build_ui()
        # setup the copy button stuff (may move this to a helper later)
        self._copy_button.setText("Copy")
        self._copy_button.setVisible(False)
        self._copy_button.clicked.connect(lambda: QGuiApplication.clipboard().setText(self._md_buffer.lstrip()))

        self._bubble.installEventFilter(self)
        self.setMouseTracking(True)

        self._pending = False
        self.set_markdown(md_buffer)


    def _build_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        msg_frame_hbox = QHBoxLayout(self)  # layout self horizontally
        msg_frame_hbox.setContentsMargins(20, 20, 20, 20)
        msg_frame_hbox.setSpacing(20)

        # organizational widget to contain the components of a chat message bubble
        bubble = QWidget(self)
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        # vertically layout the bubble
        bubble_vbox = QVBoxLayout(bubble)
        bubble_vbox.setContentsMargins(12, 12, 12, 12)
        bubble_vbox.setSpacing(12)

        # what goes inside the bubble (chat browser on top, actions below)
        browser = MessageBubble(bubble)
        actions_row = QWidget(bubble)

        actions_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

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
        scrollbar_val = self._browser.verticalScrollBar().value()
        doc = QTextDocument()
        doc.setHtml(md.render(self._md_buffer))  # parse off-screen
        self._browser.setDocument(doc)  # cheap swap
        QTimer.singleShot(0, lambda: self.set_view(scrollbar_val))

    def get_markdown(self) -> str:
        return self._md_buffer

    def set_markdown(self, text) -> None:
        self._md_buffer = text
        scrollbar_val = self._browser.verticalScrollBar().value()
        doc = QTextDocument()
        doc.setHtml(md.render(text))  # parse off-screen
        self._browser.setDocument(doc)  # cheap swap
        QTimer.singleShot(0, lambda: self.set_view(scrollbar_val))

    def set_view(self, scrollbar_current_val):
        if self._browser.autoscroll is True:
            c = self._browser.textCursor()
            c.movePosition(QTextCursor.End)
            self._browser.setTextCursor(c)
            self._browser.ensureCursorVisible()
        else:
            self._browser.verticalScrollBar().setValue(scrollbar_current_val)
        self.size_changed.emit(self.sizeHint())

    def update_boundaries(self, parent_w):                                                 #        ▲
        if parent_w:                                                  # ▲      ▲
            w = int(parent_w * 0.35)                          # ▲ ▲   ▲ ▲
            h = int(float(w) * 0.618)                   # Follow the ratio       # ▲▲ ▲ ▲ ▲ ▲ ▲▲
            print(f"updating boundaries: w:{w}x h:{h}")
            self._browser.setMaximumWidth(w)
            self._browser.setMaximumHeight(h)
            self._browser.recompute_dimensions()  # boundaries just shifted so lets recompute

    def _preprocess_think_blocks(self, text: str) -> str:
        return text.replace("<think>", "&lt;think&gt;").replace("</think>", "&lt;/think&gt;")

    # --- overrides -----------------------------------------------------

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self._copy_button.setVisible(True)
        if event.type() == QEvent.Leave:
            self._copy_button.setVisible(False)
        return super().eventFilter(obj, event)