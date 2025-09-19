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
    state = pyqtSignal(str)
    thinking = pyqtSignal(str)           # added: fix missing signal used in run()

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
            print("Beginning thread!")
            self.state.emit("busy")  # <— regular busy/connecting indicator ON

            client = InferenceClient(token=self._token, timeout=self._timeout, provider="featherless-ai")

            # If the model supports thinking, enable it via provider-specific params.
            # (These are no-ops on models that don't support them.)
            stream = client.chat.completions.create(
                model=self._model,
                messages=self._messages,
                temperature=self._temperature,
                top_p=self._top_p,
                max_tokens=self._max_tokens,
                stream=True,
                # examples:
                # OpenAI-style reasoning effort:
                # extra_body={"reasoning": {"effort": "medium"}},
                # Qwen/DeepSeek-style thinking switch:
                # extra_body={"enable_thinking": True, "thinking_budget": 128},
            )

            got_any_tokens = False
            got_answer_tokens = False
            self._full_text_parts = []
            self._reasoning_parts = []

            for chunk in stream:
                if self._stopped:
                    break
                if not chunk or not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # 1) REASONING / THINKING STREAM (provider-dependent keys)
                # vLLM / DeepSeek / Qwen-compatible:
                rc = getattr(delta, "reasoning_content", None)
                # Some providers nest it:
                r = getattr(delta, "reasoning", None)
                if r and hasattr(r, "content"):
                    rc = (rc or "") + (r.content or "")

                if rc:
                    if not got_any_tokens:
                        self.state.emit("thinking")  # <— switch UI to “thinking”
                        got_any_tokens = True
                    self._reasoning_parts.append(rc)
                    self.thinking.emit(rc)  # <— emit to a separate area in your UI
                    continue

                # 2) NORMAL ANSWER CONTENT
                piece = getattr(delta, "content", None)
                if piece:
                    if not got_any_tokens:
                        self.state.emit("responding")  # got first token (no reasoning)
                        got_any_tokens = True
                    if not got_answer_tokens:
                        # first answer token after thinking => switch to responding
                        self.state.emit("responding")
                        got_answer_tokens = True

                    self._full_text_parts.append(piece)
                    self.chunk.emit(piece)
                    continue

            final_answer = "".join(self._full_text_parts)
            final_reasoning = "".join(getattr(self, "_reasoning_parts", []))
            # If you want, expose the collected reasoning separately:
            # self.reasoning_finished.emit(final_reasoning)

            self.state.emit("done")
            self.finished.emit(final_answer)
            print("Worker done!")

        except Exception as e:
            self.state.emit("error")
            raise
        finally:
            self.state.emit("done")