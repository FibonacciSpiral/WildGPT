import multiprocessing as mp
from typing import List, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from huggingface_hub import InferenceClient
from queue import Empty


def talk_to_assistant(token, timeout, model, messages, temperature, top_p, max_tokens, result_queue):
    try:
        client = InferenceClient(token=token, timeout=timeout, provider="featherless-ai")

        _STOP_SEQS = (
            "<|im_end|>",
            "<|eot_id|>",
            "<|end_of_text|>",
            "<|im_start|>user",
            "<|im_start|>assistant",
        )

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=True,
            stop=_STOP_SEQS,
        )

        for chunk in stream:
            if not chunk or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            txt = getattr(delta, "content", None)
            if txt:
                result_queue.put(("chunk", txt))

        result_queue.put(("done", None))

    except Exception as e:
        result_queue.put(("error", e))
        result_queue.put(("done", None))


class HFChatStreamWorker(QObject):
    """
    Streams an assistant reply using Hugging Face InferenceClient (OpenAI-compatible).
    - Construct with model/token and chat messages.
    - Call run() from a QThread.
    - Emits 'chunk' as text arrives, 'finished' when done, 'error' on failure.
    - Call stop() to cancel mid-stream.
    """
    chunk = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    state = pyqtSignal(str)
    thinking = pyqtSignal(str)

    def __init__(
        self,
        model: str,
        token: Optional[str],
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.95,
        max_tokens: int = 500,
        request_timeout: int = 60,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._model = model
        self._token = token
        self._messages = messages
        self._temperature = temperature
        self._top_p = top_p
        self._max_tokens = max_tokens
        self._timeout = request_timeout
        self._stopped = False

        self._process: Optional[mp.Process] = None
        self._queue: Optional[mp.Queue] = None
        self._stop_event: Optional[mp.Event] = None

    def stop(self):
        if self._process and self._process.is_alive():
            self._process.terminate()  # kill immediately

    def run(self) -> None:

        self.state.emit("busy")

        ctx = mp.get_context("spawn")
        self._queue = ctx.Queue()

        self._stop_event = ctx.Event()

        self._process = mp.Process(
            target=talk_to_assistant,
            args=(self._token,
                  self._timeout,
                  self._model,
                  self._messages,
                  self._temperature,
                  self._top_p,
                  self._max_tokens,
                  self._queue),
            daemon=True
        )

        try:
            self._process.start()

            while True:
                try:
                    msg, payload = self._queue.get(timeout=0.1)
                except Empty:
                    if not self._process.is_alive():
                        break
                    continue

                except (EOFError, OSError):
                    # Child died abruptly; bail out.
                    break

                if msg == "chunk":
                    self.chunk.emit(payload)
                elif msg == "error":
                    self.error.emit(payload)
                elif msg == "done":
                    break

        finally:
            try:
                if self._process is not None:
                    if self._process.is_alive():
                        self._process.terminate()
                    self._process.join(timeout=2)
                    # .close() is available on spawn/forkserver contexts
                    try:
                        self._process.close()
                    except Exception:
                        pass
            finally:
                self._process = None

            try:
                if self._queue is not None:
                    self._queue.close()
                    self._queue.join_thread()
            finally:
                self._queue = None
                self._stop_event = None

            self.finished.emit()
            self.state.emit("done")
