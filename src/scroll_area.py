from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtWidgets import (
    QWidget, QSizePolicy, QListWidget, QListWidgetItem, QListView, QAbstractScrollArea
)
from PyQt5.QtGui import QResizeEvent

from src.message_frame import ChatMessageFrame, MessageFrame, ProgressIndicator


# ---- Light-weight role identifiers ----
@dataclass(frozen=True)
class ChatRole:
    USER: str = "user"
    ASSISTANT: str = "assistant"
    SYSTEM: str = "system"


# ---- Scroll area to hold messages ----
class ChatScrollArea(QListWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Style & sizing
        self.setObjectName("chatScroll")
        self.setUniformItemSizes(False)  # allow variable bubble heights
        self.setWordWrap(True)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(20)  # pixels per wheel tick
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setResizeMode(QListView.Adjust)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.setSelectionMode(QListWidget.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)


    def _append_bubble_to_stack(self, bubble: MessageFrame) -> None:
        # append after the last item
        self.insert_bubble_at_idx(bubble, self.count())

    def append_assistant_bubble_to_stack(self, text="") -> ChatMessageFrame:
        bubble = ChatMessageFrame(role=ChatRole.ASSISTANT, md_buffer=text)
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
        """
        Removes the most recently added bubble, if any.
        """
        if self.count() == 0:
            return False
        return self.remove_bubble_at_idx(self.count() - 1)

    def _update_item_size(self, item: QListWidgetItem, size: QSize):
        # we set the size of the row. Only the height actually matters
        item.setSizeHint(QSize(item.sizeHint().width(), size.height()))
        self.doItemsLayout()

    def insert_bubble_at_idx(self, frame: MessageFrame, idx: int) -> None:
        """
        Inserts a bubble wherever you want, provided the idx is valid
        :param frame:
        :param idx:
        :return:
        """
        if idx < 0 or idx > self.count():
            print("wtf you doin bro? you cannot insert a bubble into oblivion")
            return None
        frame.update_boundaries(self.width())
        item = QListWidgetItem()
        item.setSizeHint(QSize(self.width(), frame.height()))  # let row height match widget
        self.insertItem(idx, item)
        self.setItemWidget(item, frame)

        # Auto-update on resize
        frame.size_changed.connect(lambda size, i=item: self._update_item_size(i, size))
        QTimer.singleShot(50, self.scrollToBottom)

    def remove_bubble_at_idx(self, idx: int) -> bool:
        """
        Removes a bubble wherever you want, provided the idx is valid
        :param idx:
        :return:
        """
        if idx < 0 or idx >= self.count():
            print("wtf you doin bro? you cannot remove a non-existent bubble")
            return False

        item = self.item(idx)
        bubble = self.itemWidget(item)
        if bubble is not None:
            self.removeItemWidget(item)  # detach widget from the item
            bubble.setParent(None)  # orphan it
            bubble.deleteLater()  # schedule deletion
        self.takeItem(idx)  # remove the QListWidgetItem itself

        QTimer.singleShot(50, self.scrollToBottom)
        return True

    def peek_most_recent(self) -> Optional[MessageFrame]:
        """
        Returns the most recently added bubble, or None if empty.
        """
        if self.count() == 0:
            return None
        return self.get_frame_at_idx(self.count() - 1)

    def get_frame_at_idx(self, idx: int) -> Optional[MessageFrame]:
        """
        Returns the bubble widget at the given index, or None if invalid.
        """
        if idx < 0 or idx >= self.count():
            return None

        item = self.item(idx)
        return self.itemWidget(item)


    def append_to_assistant(self, chunk: str) -> None:
        """
        Appends a chunk of markdown content to the current assistant message.
        If a progress indicator is the last item, it is removed.
        If the last message is from the user or nothing is there, a new assistant bubble is appended.
        """
        last_bubble = self.peek_most_recent()

        if isinstance(last_bubble, ChatMessageFrame):
            if last_bubble.role == ChatRole.ASSISTANT:
                # Append to existing assistant message
                last_bubble.append_markdown(chunk)
                return
            elif last_bubble.role == ChatRole.USER:
                # Start a new assistant message in reply to user
                self.append_assistant_bubble_to_stack(chunk)
                return

        elif isinstance(last_bubble, ProgressIndicator):
            # Remove the loading indicator before continuing
            removed = self.remove_most_recent()
            if not removed:
                print("Could not remove progress indicator before appending assistant message.")
            else:
                # After removing, re-check the new last bubble
                return self.append_to_assistant(chunk)
            
        # currently no handling for other types of bubbles

        # todo make sure every bubble has its own name
        print("Oh my God what did you do? -> in append_to_assistant: last_bubble=%s", type(last_bubble).__name__)


    def finish_assistant_stream(self):
        last_bubble = self.peek_most_recent()
        if isinstance(last_bubble, ChatMessageFrame) and last_bubble.role == ChatRole.ASSISTANT:
            return last_bubble.get_markdown()
        else:
            print("Holy fuck. Tried to close down assistant stream and last bubble is not the assistant bubble.")
            return None

    def clear_messages(self) -> None:
        """
        Removes all bubbles from the chat list.
        """
        self.clear()  # removes all QListWidgetItems (and their widgets)
        QTimer.singleShot(0, self.scrollToBottom)

    def scroll_to_bottom(self) -> None:
        self.scrollToBottom()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        for i in range(self.count()):
            frame = self.get_frame_at_idx(i)
            if frame:
                frame.update_boundaries(self.width())
                item = self.item(i)
                item.setSizeHint(QSize(self.width(), frame.height()))
