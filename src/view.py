from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt, QStandardPaths, QSize, QUrl
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, QMessageBox, QFileDialog, QDialog, QLabel, QToolButton
)

from src.input_bar import ChatInputBar
from src.scroll_area import ChatScrollArea
from src.theme_manager import ThemeManager, Theme
from src.top_bar import TopBar


# ---- Main Chat Window (View) ----
class ChatWindow(QMainWindow):
    # Outgoing (to Controller)
    sendMessage = pyqtSignal(str)
    stopRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    modelChanged = pyqtSignal(str)
    saveChatRequested = pyqtSignal()
    loadChatRequested = pyqtSignal()
    pickPersonalityRequested = pyqtSignal()
    createPersonalityRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wild GPT")
        self.setWindowIcon(QIcon("./Dependencies/wildAI.png"))
        self._build_ui()
        self.set_theme(ThemeManager.DARK)
        self.current_model = "deepseek-ai/DeepSeek-V3-0324"
        self.update_model(self.top_bar.model_combo.currentText())
        self.temperature = float(self.top_bar.temp_spin.value())

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("central")
        vbox = QVBoxLayout(central)  #maybe update to gridlayout?
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
       # central.setStyleSheet("border: 1px dashed red;") #uncomment for layout debugging!

        self.top_bar = TopBar(self)
        self.top_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.top_bar.setMaximumHeight(100)
        self.chat_stack = ChatScrollArea(self)
        self.input_bar = ChatInputBar(self)
        self.input_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # if you still want the input bar horizontally centered, wrap it
        self.input_pane = QWidget(self)
        self.input_pane.setObjectName("inputPane")
        hbox = QHBoxLayout(self.input_pane)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        self.input_pane.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hbox.addWidget(self.input_bar, 0, alignment=Qt.AlignHCenter)


        # --- assemble main layout ---
        vbox.addWidget(self.top_bar)
        vbox.addWidget(self.chat_stack)
        vbox.addWidget(self.input_pane)
        self.setCentralWidget(central)

        self.input_bar.userMsgSentSignal.connect(self.sendMessage)
        self.input_bar.stopRequested.connect(self.stopRequested)
        self.input_bar.clearRequested.connect(self.clearRequested)
        self.top_bar.modelChanged.connect(self.update_model)
        self.top_bar.settingsChanged.connect(self.update_settings)
        self.top_bar.saveChatRequested.connect(self.saveChatRequested)
        self.top_bar.loadChatRequested.connect(self.loadChatRequested)
        self.top_bar.pickPersonalityRequested.connect(self.pickPersonalityRequested)
        self.top_bar.createPersonalityRequested.connect(self.createPersonalityRequested)

    # -------- Public slots --------
    def add_user_message(self, text: str) -> None:
        self.chat_stack.append_user_bubble_to_stack(text)

    def add_assistant_message(self, text: str) -> None:
        self.chat_stack.append_assistant_bubble_to_stack(text)

    def add_progress_indicator(self)-> None:
        self.chat_stack.append_progress_indicator_to_stack()

    def append_assistant_stream(self, chunk) -> None:
        self.chat_stack.append_to_assistant(chunk)

    def finish_assistant_stream(self) -> str:
        return self.chat_stack.finish_assistant_stream()

    def set_busy(self, busy: bool) -> None:
        self.input_bar.set_busy(busy)
        self.top_bar.set_busy(busy)

    def is_busy(self):
        return self.input_bar.busy_state

    def set_theme(self, theme: Theme) -> None:
        """Public API to switch theme at runtime."""
        if theme is not None:
            ThemeManager.apply_palette(QApplication.instance(), theme)  # type: ignore[arg-type]
            self.setStyleSheet(ThemeManager.stylesheet(theme))

    def on_clear_clicked(self) -> None:
        self.chat_stack.clear_messages()

    def update_model(self, new_model):
        self.current_model = str(new_model)

    def update_settings(self, new_settings: dict) -> None:
        for setting_name, value in new_settings.items():
            if setting_name == "temperature":
                self.temperature = value

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.input_bar.update_boundaries(self.width(), self.height())

    def ask_save_before_new(self) -> int:
        """Ask user if they want to save before starting a new chat."""
        response =  QMessageBox.question(
            self,
            "Save Chat?",
            "Do you want to save the current chat before starting a new one?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )

        if response == QMessageBox.Yes:
            return True
        elif response == QMessageBox.No:
            return False
        else:
            return None

    def choose_save_location(self, default_dir="./", name="3====O---") -> str:
        """Open a Save dialog defaulting to a JSON filename and return the chosen path ('' if canceled)."""
        dlg = QFileDialog(self, "Save File")
        dlg.setAcceptMode(QFileDialog.AcceptSave)  # Save instead of Open
        dlg.setNameFilters(["JSON Files (*.json)", "All Files (*)"])

        # Use Qt's dialog (not native) so we can show min/max (collapse/expand) buttons
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)
        dlg.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        dlg.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        parent_width = self.width()

        min_w = int(parent_width * 0.7)
        min_h  = int(0.5 * parent_width)

        dlg.setMinimumSize(QSize(min_w, min_h))

        home = Path.home()

        # Sidebar entries
        sidebar_urls = [
            QUrl.fromLocalFile("C:/"),  # C drive
            QUrl.fromLocalFile(str(home / "Downloads")),
            QUrl.fromLocalFile(str(home / "Documents")),
            QUrl.fromLocalFile(str(home / "Desktop")),
            QUrl.fromLocalFile(str(home / "OneDrive"))
        ]

        dlg.setSidebarUrls(sidebar_urls)

        # Default starting folder + suggested filename
        dlg.setDirectory(str(default_dir))
        dlg.selectFile(f"{name}.json")

        if dlg.exec() == QDialog.Accepted:
            path = dlg.selectedFiles()[0]
            if not path.lower().endswith(".json"):
                path += ".json"
            return path
        return ""
    
    def choose_open_location(self, default_dir="./", name="") -> str:
        """Open a Open dialog defaulting to a JSON filename and return the chosen path ('' if canceled)."""
        dlg = QFileDialog(self, "Open File")
        dlg.setAcceptMode(QFileDialog.AcceptOpen)  # Open instead of Save
        dlg.setNameFilters(["JSON Files (*.json)", "All Files (*)"])

        # Use Qt's dialog (not native) so we can show min/max (collapse/expand) buttons
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)
        dlg.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        dlg.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        parent_width = self.width()

        min_w = int(parent_width * 0.7)
        min_h  = int(0.5 * parent_width)

        dlg.setMinimumSize(QSize(min_w, min_h))

        home = Path.home()

        # Sidebar entries
        sidebar_urls = [
            QUrl.fromLocalFile("C:/"),  # C drive
            QUrl.fromLocalFile(str(home / "Downloads")),
            QUrl.fromLocalFile(str(home / "Documents")),
            QUrl.fromLocalFile(str(home / "Desktop")),
            QUrl.fromLocalFile(str(home / "OneDrive"))
        ]

        dlg.setSidebarUrls(sidebar_urls)

        # Default starting folder + suggested filename
        dlg.setDirectory(str(default_dir))
        dlg.selectFile(f"{name}")

        if dlg.exec() == QDialog.Accepted:
            path = dlg.selectedFiles()[0]
            return path
        return ""

    def show_error(self, title: str, message: str):
        """Display an error message box."""
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        """Display an informational message box."""
        QMessageBox.information(self, title, message)

