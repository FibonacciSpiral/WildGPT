
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
import sys
import threading
import time
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt5.QtCore import QThread

from controller import Controller

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel, QPlainTextEdit,
    QStyle, QHBoxLayout, QVBoxLayout, QSizePolicy
)

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


# todo add a standard style sheet for the exceptionDialog
class ExceptionDialog(QDialog):
    def __init__(self, message: str, details: str, parent=None):
        super().__init__(parent)
        self._choice = "continue"
        self.setWindowTitle("Unexpected Error")
        self.setWindowModality(Qt.ApplicationModal)
        # Make it clearly resizable
        self.setSizeGripEnabled(True)
        self.setMinimumSize(520, 360)
        self.setWindowIcon(QIcon("wildAI.ico"))
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )

        # --- Header: icon + message ---
        icon = self.style().standardIcon(QStyle.SP_MessageBoxCritical)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon.pixmap(40, 40))
        icon_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        msg_lbl = QLabel(message or "Unexpected Error")
        msg_lbl.setWordWrap(True)

        sub_lbl = QLabel("Close to continue using the app, or Quit to exit.")
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: gray;")

        header_text = QVBoxLayout()
        header_text.addWidget(msg_lbl)
        header_text.addWidget(sub_lbl)

        header = QHBoxLayout()
        header.addWidget(icon_lbl)
        header.addLayout(header_text)
        header.addStretch(1)

        # --- Details area (expandable, scrollable) ---
        details_edit = QPlainTextEdit(details or "")
        details_edit.setReadOnly(True)
        details_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.Monospace)
        details_edit.setFont(mono)

        # --- Buttons ---
        buttons = QDialogButtonBox()
        close_btn = buttons.addButton("Close", QDialogButtonBox.AcceptRole)
        quit_btn = buttons.addButton("Quit", QDialogButtonBox.DestructiveRole)
        copy_btn = buttons.addButton("Copy details", QDialogButtonBox.ActionRole)

        close_btn.clicked.connect(self.accept)
        def _quit():
            self._choice = "quit"
            self.accept()
        quit_btn.clicked.connect(_quit)

        def _copy():
            QApplication.clipboard().setText(details_edit.toPlainText())
        copy_btn.clicked.connect(_copy)

        # --- Layout ---
        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addWidget(details_edit)
        root.addWidget(buttons)

        # Default focus & button
        close_btn.setDefault(True)

        # --- per-class stylesheet (scoped to this dialog subtree) ---
        self.setStyleSheet("""
               /* Root dialog */
               QDialog#ExceptionDialog {
                   background: palette(base);
                   border: 1px solid palette(mid);
                   border-radius: 12px;
               }

               /* Optional theme based on dynamic property */
               QDialog#ExceptionDialog[severity="critical"] {
                   border: 1px solid #d9534f;
               }

               /* Header */
               QLabel#message {
                   font-weight: 600;
                   font-size: 14pt;
               }
               QLabel#subtitle {
                   color: palette(mid);
                   margin-top: 2px;
               }
               QLabel#icon {
                   margin-right: 12px;
               }

               /* Details area */
               QPlainTextEdit#details {
                   background: palette(alternate-base);
                   border: 1px solid palette(mid);
                   border-radius: 8px;
                   padding: 6px;
               }

               /* Buttons */
               QDialogButtonBox QPushButton {
                   padding: 6px 12px;
                   border-radius: 8px;
               }
               QDialogButtonBox QPushButton:default {
                   font-weight: 600;
               }
               """)

    @property
    def choice(self) -> str:
        return self._choice


def show_exception_dialog(message: str, details: str) -> str:
    """Present a resizable critical error dialog; return 'continue' or 'quit'."""
    parent = QApplication.activeWindow()
    dlg = ExceptionDialog(message, details, parent)
    dlg.resize(1000, 600)  # nice starting size; user can resize
    dlg.exec_()
    return dlg.choice


_handling_guard = False  # low-level recursion guard only


# --- GUI-thread bridge for showing the dialog ---------------------------------
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt



class _DialogBridge(QObject):
    show_dialog = pyqtSignal(str, str)  # (message, details)

    def __init__(self):
        super().__init__()
        self.show_dialog.connect(self._on_show, Qt.QueuedConnection)

    @pyqtSlot(str, str)
    def _on_show(self, message: str, details: str) -> None:
        try:
            choice = show_exception_dialog(message=message, details=details)
            if choice == "quit":
                QApplication.instance().quit()
        finally:
            _exc_mgr.on_closed()

_dialog_bridge: _DialogBridge | None = None

def handle_exception(exc_type, exc_value, exc_tb) -> None:
    """Central unhandled-exception hook: log, show dialog, optionally quit."""
    global _handling_guard, _dialog_bridge

    if _handling_guard:
        traceback.print_exception(exc_type, exc_value, exc_tb)
        return

    _handling_guard = True
    try:
        # Always print something to the console, even if logging isn't ready yet.
        traceback.print_exception(exc_type, exc_value, exc_tb)
        if not _logger.handlers:
            import logging, sys
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            _logger.addHandler(h)

        details = exception_to_text(exc_type, exc_value, exc_tb)
        _logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

        # Ensure we have an app and remember if we just created it.
        existing_app = QApplication.instance()
        created_temp_app = existing_app is None
        app = existing_app or QApplication(sys.argv)

        # Ensure our bridge lives in the GUI thread.
        if _dialog_bridge is None:
            _dialog_bridge = _DialogBridge()
            _dialog_bridge.moveToThread(app.thread())

        # Decide debouncing BEFORE posting to the GUI thread.
        if not _exc_mgr.should_show(exc_type, exc_value):
            return

        message = str(exc_value) or exc_type.__name__

        # If we're already on the GUI thread, call directly; else, emit queued.
        if QThread.currentThread() is app.thread():
            _dialog_bridge._on_show(message, details)
        else:
            _dialog_bridge.show_dialog.emit(message, details)

        # If we created a temporary app for startup-time errors, run its loop
        # so the modal dialog can actually appear.
        if created_temp_app:
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
        threading.excepthook = _thread_hook

    app.controller = Controller()  # app.controller is just a placeholder for Controller to live
    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        # Last-resort guard for startup-time errors before hooks are active.
        handle_exception(*sys.exc_info())
        sys.exit(1)
