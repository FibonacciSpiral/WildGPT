import os
from typing import Optional, List, Dict

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QWidget
from stream_worker import HFChatStreamWorker
from view import ChatWindow  # adjust import to your path

# --- Your existing config (kept as-is) --------------------------------------
MODEL = os.environ.get("HF_MODEL", "deepseek-ai/DeepSeek-V3-0324")
HF_TOKEN = os.environ.get("HF_TOKEN")  # optional if you've run `hf auth login`
SYSTEM_PROMPT = "You are a helpful, concise assistant."

class Controller(QWidget):
    def __init__(self):
        super().__init__()
        self.view = ChatWindow()
        self.view.showMaximized()

        # chat history (OpenAI-style)
        self._messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # connections
        self.view.sendMessage.connect(self.on_send)
        self.view.stopRequested.connect(self.on_stop)
        self.view.clearRequested.connect(self.on_clear)

        # streaming members
        self._thread: Optional[QThread] = None
        self._worker: Optional[HFChatStreamWorker] = None

    def _start_stream(self) -> None:
        """Proof of concept: just append a fixed assistant reply."""
        hardcoded_reply = "This is a hardcoded assistant message for demo.We have a  colleague at work for a few months now and everyone seems to love her, seek out her company, they already have inside jokes with her and some people even eat with her not in cafeteria.She's got to be the most obnoxious person I have ever met. She keeps constantly chitchatting instead of working, never really does her proper research when reporting a problem and is absolutely confidently wrong. Seriously, I have never met someone who would be this unlikable to work with. I have been ignoring her when it's not work related and meet her energy when she tries to dump on me something that has nothing to do with me and she has started avoiding me (thank goodness) unless necessary.But I just completely fail to understand why she would be so likable. She's so infuriating to me and yet I hear the office she's in constantly laughing and chatting. It annoys me because that means they're neglecting their work and consequences of that ultimately fall on me.This isn't a normal chitchat either. It's okay to take a break and joke with your colleagues but she regularly does this for 30 minutes or MORE. Even our lunch break is just 30 minutes and she regularly takes longer breaks during the day to talk.If being likable means behaving like this then this person has completely cured me of my desire to be popular."
        self.view.add_assistant_message(hardcoded_reply)
        # # clean any old worker
        # self.on_stop()
        #
        # # create worker with current history
        # self._worker = HFChatStreamWorker(
        #     model=MODEL,
        #     token=HF_TOKEN,
        #     messages=self._messages,
        #     temperature=0.7,
        #     top_p=0.95,
        #     max_tokens=500,
        #     request_timeout=60,
        # )
        # self._thread = QThread(self)
        # self._worker.moveToThread(self._thread)
        #
        # # wire
        # self._thread.started.connect(self._worker.run)
        # self._worker.chunk.connect(self.view.append_assistant_stream)
        # self._worker.finished.connect(self._on_stream_finished)
        # self._worker.error.connect(self._on_stream_error)
        #
        # # cleanup
        # self._worker.finished.connect(self._cleanup_stream)
        # self._worker.error.connect(self._cleanup_stream)
        # self._thread.finished.connect(self._thread.deleteLater)
        #
        # # UI state
        # self.view.set_busy(True)
        # self._thread.start()

    def _cleanup_stream(self) -> None:
        if self._worker:
            self._worker.deleteLater()
        if self._thread:
            self._thread.quit()
            self._thread.wait(200)
        self._worker = None
        self._thread = None
        self.view.finish_assistant_stream()
        self.view.set_busy(False)

    # ---- UI handlers ----
    def on_send(self, text: str) -> None:
        self.view.add_user_message(text)
        self._messages.append({"role": "user", "content": text})
        self._start_stream()

    def on_stop(self) -> None:
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(200)
        self._worker = None
        self._thread = None
        self.view.finish_assistant_stream()
        self.view.set_busy(False)

    def on_clear(self) -> None:
        self._messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        # (view already cleared)

    # ---- stream completions ----
    def _on_stream_finished(self, full_text: str) -> None:
        # append assistant message to history
        self._messages.append({"role": "assistant", "content": full_text})

    def _on_stream_error(self, msg: str) -> None:
        # optional: show in UI bubble or a toast
        self.view.append_assistant_stream(f"\n[error] {msg}\n")