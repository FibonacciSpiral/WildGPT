# file: main.py
"""PyQt5 entrypoint with robust exception handling, GUI dialog, and file logging.

Why this structure:
- `SafeApplication.notify` catches exceptions inside Qt's event loop so the app can continue.
- `sys.excepthook` and `threading.excepthook` catch uncaught errors elsewhere.
- A modal `QMessageBox` offers Close (continue) or Quit, and shows the full traceback in Details.
- Rotating file logger writes errors to ./logs/errors.log for supportability.
- Debounce/guard ensures the dialog isn't re-opened repeatedly, so you *can* close and continue.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from controller import Controller

# --- Logging setup -----------------------------------------------------------
LOG_DIR = Path.cwd() / "logs"
LOG_FILE = LOG_DIR / "errors.log"

_logger = logging.getLogger("app")


def setup_logging() -> None:
    """Configure a rotating file logger.

    Why: Ensures error history persists without unbounded growth.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _logger.setLevel(logging.INFO)

    if not any(isinstance(h, RotatingFileHandler) for h in _logger.handlers):
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(fmt)
        _logger.addHandler(file_handler)

    # Console output is helpful during development.
    if not any(isinstance(h, logging.StreamHandler) for h in _logger.handlers):
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        _logger.addHandler(console)


# --- Exception handling state/logic -----------------------------------------
class _ExceptionManager:
    """Debounce and guard exception UI so you can close & continue.

    Why: Prevents dialog storms caused by the same exception firing repeatedly
    (e.g., from timers/paint events). Ensures only one dialog is visible at a time.
    """

    def __init__(self) -> None:
        self.dialog_open = False
        self.last_sig: tuple[str, str] | None = None
        self.last_shown = 0.0
        self.cooldown_sec = 1.0

    def should_show(self, exc_type: type[BaseException], exc_value: BaseException) -> bool:
        now = time.monotonic()
        sig = (exc_type.__name__, str(exc_value))
        if self.dialog_open:
            return False
        if self.last_sig == sig and (now - self.last_shown) < self.cooldown_sec:
            return False
        self.last_sig = sig
        self.last_shown = now
        self.dialog_open = True
        return True

    def on_closed(self) -> None:
        self.dialog_open = False


_exc_mgr = _ExceptionManager()


def exception_to_text(exc_type, exc_value, exc_tb) -> str:
    """Return a readable traceback string for the Details panel."""
    return "".join(traceback.format_exception(exc_type, exc_value, exc_tb))


def show_exception_dialog(message: str, details: str) -> str:
    """Present a critical error dialog and return "continue" or "quit".

    Why: Allows users to keep working if the error is non-fatal.
    """
    parent = QApplication.activeWindow()
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle("Unexpected Error")
    box.setText(message)
    box.setInformativeText(
        "Close to continue using the app, or Quit to exit."
    )
    box.setDetailedText(details)
    box.setWindowModality(Qt.ApplicationModal)

    close_btn = box.addButton("Close", QMessageBox.AcceptRole)  # continue
    quit_btn = box.addButton("Quit", QMessageBox.DestructiveRole)
    box.setDefaultButton(close_btn)

    box.exec_()
    return "quit" if box.clickedButton() is quit_btn else "continue"


_handling_guard = False  # low-level recursion guard only


def handle_exception(exc_type, exc_value, exc_tb) -> None:
    """Central unhandled-exception hook: log, show dialog, optionally quit.

    Debounced: will not show another dialog while one is open, or if the
    exact same error repeats within a short cooldown window.
    """
    global _handling_guard
    if _handling_guard:
        traceback.print_exception(exc_type, exc_value, exc_tb)
        return

    _handling_guard = True
    try:
        details = exception_to_text(exc_type, exc_value, exc_tb)
        _logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

        app = QApplication.instance() or QApplication(sys.argv)

        def _show():
            try:
                if not _exc_mgr.should_show(exc_type, exc_value):
                    return
                choice = show_exception_dialog(
                    message=str(exc_value) or exc_type.__name__, details=details
                )
                if choice == "quit":
                    app.quit()
            finally:
                _exc_mgr.on_closed()

        # Ensure dialog runs on the GUI thread.
        QTimer.singleShot(0, _show)

        # If we had to create a temporary app, we need a loop to show the dialog.
        if not QApplication.instance():
            app.exec_()

    finally:
        _handling_guard = False


# --- Application subclass ----------------------------------------------------
class SafeApplication(QApplication):
    """QApplication that converts Qt event-handler exceptions into dialogs.

    Why: Qt swallows exceptions raised in event handlers; overriding `notify`
    ensures they are surfaced consistently.
    """

    def notify(self, receiver, event):  # type: ignore[override]
        try:
            return super().notify(receiver, event)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            handle_exception(exc_type, exc_value, exc_tb)
            return True  # swallow the error to keep event loop alive


# --- Entrypoint --------------------------------------------------------------

def main(argv: list[str]) -> int:
    setup_logging()

    app = SafeApplication(argv)

    # Global hooks for uncaught exceptions
    sys.excepthook = handle_exception

    if hasattr(threading, "excepthook"):
        def _thread_hook(args: threading.ExceptHookArgs) -> None:
            handle_exception(args.exc_type, args.exc_value, args.exc_traceback)
        threading.excepthook = _thread_hook  # type: ignore[attr-defined]

    demo = Controller()
    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        # Last-resort guard for startup-time errors before hooks are active.
        handle_exception(*sys.exc_info())
        sys.exit(1)



# def main():
#     client = InferenceClient(token=HF_TOKEN)
#
#     # Chat history follows OpenAI-style roles
#     messages = [{"role": "system", "content": SYSTEM_PROMPT}]
#
#     print(f"Connected to {MODEL}. Type 'exit' or 'quit' to leave.\n")
#
#     while True:
#         try:
#             user = input("You: ").strip()
#         except (EOFError, KeyboardInterrupt):
#             print("\nBye!")
#             break
#
#         if user.lower() in {"exit", "quit"}:
#             print("Bye!")
#             break
#         if not user:
#             continue
#
#         # Append user message
#         messages.append({"role": "user", "content": user})
#
#         # --- Non-streaming (simple) ---
#         try:
#             completion = client.chat.completions.create(
#                 model=MODEL,
#                 messages=messages,
#                 max_tokens=500,      # adjust as you like
#                 temperature=0.7,     # creativity
#                 top_p=0.95,
#             )
#         except Exception as e:
#             print(f"[error] {e}")
#             # On some errors (e.g., token/permission), you may want to pop the last user msg
#             messages.pop()
#             continue
#
#         reply = completion.choices[0].message.content
#         print(f"DeepSeek: {reply}\n")
#
#         # Add assistant reply to history so it has context for the next turn
#         messages.append({"role": "assistant", "content": reply})
#
# if __name__ == "__main__":
#     main()
