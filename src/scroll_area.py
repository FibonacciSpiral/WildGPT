from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QScrollArea,
    QWidget, QFrame, QVBoxLayout, QSizePolicy
)

from src.message_frame import ChatMessageFrame, MessageFrame, ProgressIndicator

# ---- Light-weight role identifiers ----
@dataclass(frozen=True)
class ChatRole:
    USER: str = "user"
    ASSISTANT: str = "assistant"
    SYSTEM: str = "system"


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

    def _append_bubble_to_stack(self, bubble: MessageFrame) -> None:
        """
        Simply inserts a bubble at the bottom of the chat stack
        :param bubble:
        :return:
        """
        self.insert_bubble_at_idx(bubble, self._chat_stack_layout.count() - 1)

    def append_assistant_bubble_to_stack(self, text="") -> ChatMessageFrame:
        bubble = ChatMessageFrame(ChatRole.ASSISTANT, text)
        self._append_bubble_to_stack(bubble)  #make sure the assistant is able to append html
        return bubble

    def append_user_bubble_to_stack(self, text):
        bubble = ChatMessageFrame(ChatRole.USER, text)
        self._append_bubble_to_stack(bubble)
        return bubble

    def append_progress_indicator_to_stack(self):
        indicator = ProgressIndicator(ChatRole.SYSTEM)
        self._append_bubble_to_stack(indicator)  # make sure the assistant is able to append html
        return indicator    # probably does not need to return the indicator...

    def remove_most_recent(self) -> bool:
        return self.remove_bubble_at_idx(self._chat_stack_layout.count() - 2)

    def insert_bubble_at_idx(self, bubble: MessageFrame, idx: int) -> None:
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

    def remove_bubble_at_idx(self, idx: int) -> bool:
        """
        Removes a bubble wherever you want, provided the idx is valid
        :param idx:
        :return:
        """
        success = False
        bottom_of_stack = self._chat_stack_layout.count() - 1
        if idx > bottom_of_stack or idx < 0:
            print("wtf you doin bro? you cannot remove a non existent bubble")
            return False

        bubble = self._chat_stack_layout.itemAt(idx).widget()
        if bubble is not None:
            self._chat_stack_layout.removeWidget(bubble)
            bubble.setParent(None)
            bubble.deleteLater()
            success = True

        QTimer.singleShot(50, self.scroll_to_bottom)
        return success

    def peek_most_recent(self) -> MessageFrame | None:
        idx = self._chat_stack_layout.count() - 2
        return self.get_frame_at_idx(idx)

    def get_frame_at_idx(self, idx) -> MessageFrame | None:
        if idx >= 0:
            w = self._chat_stack_layout.itemAt(idx).widget()
        else:
            w = None
        return w

    def append_to_assistant(self, chunk) -> None:
        last_bubble = self.peek_most_recent()

        if isinstance(last_bubble, ChatMessageFrame) and last_bubble.role == ChatRole.ASSISTANT:
            chat_assistant_bubble = last_bubble
            chat_assistant_bubble.append_markdown(chunk)
        elif isinstance(last_bubble, MessageFrame) and last_bubble.role == ChatRole.SYSTEM:
            success = self.remove_most_recent()  # get rid of system bubble which is likely a progress indicator
            if success:
                self.append_to_assistant(chunk)
            else:
                print("Failed to system bubble!")
        elif isinstance(last_bubble, ChatMessageFrame) and last_bubble.role == ChatRole.USER:
            self.append_assistant_bubble_to_stack(chunk)
        else:
            print("hmmm if this happens, well you broke the code buddy. FIX IT")

    def finish_assistant_stream(self):
        last_bubble = self.peek_most_recent()
        if isinstance(last_bubble, ChatMessageFrame) and last_bubble.role == ChatRole.ASSISTANT:
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