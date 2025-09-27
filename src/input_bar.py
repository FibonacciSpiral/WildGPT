from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QTimer, QEvent, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QPushButton,
    QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy
)

from src.minimum_size_browser import InputChatBubble

class HSpacer(QWidget):
    """
    Horizontal spacer that can be used to help align widgets
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # todo make sure this is okay
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # don’t block clicks
        self.setStyleSheet("background: transparent; border: none;")

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
        self.busy_state = False
        QTimer.singleShot(0, self.input_bubble.setFocus)

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
        if self.busy_state is True:  # we don't send stuff if the assistant is busy chatting
            return
        text = self.input_bubble.toMarkdown()
        if text:
            self.userMsgSentSignal.emit(text)
            self.input_bubble.clear()

    def set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.busy_state = busy

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