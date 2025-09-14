from typing import List, Dict, Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from huggingface_hub import InferenceClient


class HFChatStreamWorker(QObject):
    """
    Streams an assistant reply using Hugging Face InferenceClient (OpenAI-compatible).
    - Construct with model/token and chat messages.
    - Call run() from a QThread.
    - Emits 'chunk' as text arrives, 'finished' when done, 'error' on failure.
    - Call stop() to cancel mid-stream.
    """
    chunk = pyqtSignal(str)
    finished = pyqtSignal(str)           # full text
    error = pyqtSignal(str)

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
        self._full_text_parts: List[str] = []

    def stop(self) -> None:
        # 'why': cooperative cancel; the API call is blocking between chunks,
        # but we stop appending/emitting and bail at the next opportunity.
        self._stopped = True

    def run(self) -> None:
        try:
            client = InferenceClient(token=self._token, timeout=self._timeout, provider="featherless-ai")
            stream = client.chat.completions.create(
                model=self._model,
                messages=self._messages,
                temperature=self._temperature,
                top_p=self._top_p,
                max_tokens=self._max_tokens,
                stream=True,
            )
            for chunk in stream:
                if self._stopped:
                    break
                # OpenAI-compatible delta structure
                if not chunk or not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", None)
                if piece:
                    self._full_text_parts.append(piece)
                    self.chunk.emit(piece)
            self.finished.emit("".join(self._full_text_parts))
        except Exception as e:
            self.error.emit(str(e))
