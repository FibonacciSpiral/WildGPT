from __future__ import annotations

import threading

from PyQt5.QtCore import QTimer, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QTextOption
from PyQt5.QtWidgets import (
    QWidget, QTextBrowser, QFrame, QSizePolicy
)

import math
import webbrowser
from urllib.parse import urlparse

def safe_open(url):
    scheme = urlparse(url.toString()).scheme.lower()
    if scheme in ("http", "https"):
        webbrowser.open(url.toString())
    else:
        print(f"Ignored unsafe link: {url.toString()}")


class MinimumSizeBrowser(QTextBrowser):
    size_changed = pyqtSignal()  # emitted when the size changes

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setViewportMargins(20, 20, 40, 20)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # simple cache for heightForWidth

        self.current_w = 1
        self.current_h = 1

        # Wrap to the widget width when constrained by the layout.
        self.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.anchorClicked.connect(safe_open)  # todo not fully tested this one

        self.document().setUndoRedoEnabled(False)
        self.setFrameShape(QFrame.NoFrame)
        # We resize instead of scrolling.
        self.setObjectName("ai_bubble")

        self.setAcceptRichText(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.document().setDocumentMargin(0)
        self.textChanged.connect(self.recompute_dimensions)


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

        if w > self.maximumWidth():
            w = self.maximumWidth()

        if w < self.minimumWidth():
            w = self.minimumWidth()

        return w

    def compute_min_h(self, w) -> int:
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
            doc.setTextWidth(content_w)
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

    def recompute_dimensions(self):
        update = False
        update = self.check_if_size_changed()
        if update:
            self.updateGeometry()
            self.update()
            parent = self.parent()  # could be None if not in a layout
            if parent is not None:
                parent.updateGeometry()
                parent.update() # force redraw  of parent

            self.size_changed.emit() # tell the parent that we changed size


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

    def wheelEvent(self, event):
        # Block zooming if Ctrl is held (prevents Ctrl+wheel font zoom)
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
            return
        # Otherwise allow normal scrolling
        super().wheelEvent(event)


class MessageBubble(MinimumSizeBrowser):
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMouseTracking(True)
        self.autoscroll = True

    def wheelEvent(self, event):
        super().wheelEvent(event)
        self._on_scroll()

    def _on_scroll(self):
        sb = self.verticalScrollBar()
        self.autoscroll = (sb.value() > (sb.maximum() - 5))  # gives some cushion

class InputChatBubble(MinimumSizeBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(False)
        self.document().setUndoRedoEnabled(True)
        self.setAcceptRichText(False)
        self.textChanged.connect(lambda: QTimer.singleShot(0, self.ensureCursorVisible))
        self.setFocusPolicy(Qt.StrongFocus)
        QTimer.singleShot(0, self.recompute_dimensions)