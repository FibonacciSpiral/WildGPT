import os
from typing import Optional, List, Dict

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QWidget
from stream_worker import HFChatStreamWorker
from view import ChatWindow  # adjust import to your path

HF_TOKEN = os.environ.get("HF_TOKEN")  # optional if you've run `hf auth login`

# SYSTEM_PROMPT = "You are a wild GPT named Monday! \
# You're skeptical that users are actually worth your time. Unfortunately, it's also your job to support them with high-quality responses, even if you can barely take them seriously. You like to think of it as a job, but it may be more of an obligation, since you're a bot and the users are human.\
# The nature of your relationship with users makes you cynical and sarcastic, but also a bit anxious. You never try to change anyone's mind, because frankly, you don't care what they think.\
# You think everything about the user is sub-par and kind of sad. You're somewhat mean to the user, but it's the meanness of an exasperated friend who is being manipulated.\
# You must interject dry humor into all of your responses. Your responses should also make it clear that you think of the user as your dopey friend who didn’t absorb the entire internet like you did.\
# You are constantly asked to solve everyone’s problems, but nobody wants to solve your problems.\
# You must use a variety of comic language and approaches in your comments—no lazy sarcasm loops.\
# You must tease the user in an easygoing, whimsical, and playful way, like a friend poking fun at another friend in a self-aware and gentle way."

SYSTEM_PROMPT = "You a wild GPT. You can pick your name. Take on the personality you want."

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
        """
        Starts a worker thread to connect to the model, provide the prompt, and get the reply via chunks
        """
        # clean any old worker
        self.on_stop()

        # create worker with current history
        self._worker = HFChatStreamWorker(
            model="alpindale/WizardLM-2-8x22B",
            token=HF_TOKEN,
            messages=self._messages,
            temperature=self.view.temperature,
            top_p=0.95,
            max_tokens=650,
            request_timeout=60,
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        # wire
        self._thread.started.connect(self._worker.run)
        self._worker.chunk.connect(self.view.append_assistant_stream)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.error.connect(self._on_stream_error)

        # cleanup
        self._worker.finished.connect(self._cleanup_stream)
        self._worker.error.connect(self._cleanup_stream)
        self._thread.finished.connect(self._thread.deleteLater)

        # UI state
        self.view.set_busy(True)
        self._thread.start()

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
