from typing import List, Dict, Optional
from PyQt5.QtCore import Qt, QSettings, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QSplitter, QWidget, QPlainTextEdit, QTabWidget,
    QDialogButtonBox, QCheckBox, QSizePolicy
)

class PersonalityPickerDialog(QDialog):
    """
    A roomier, more useful personality picker with:
      - Resizable split layout (list on the left, preview on the right)
      - Live search/filter
      - Larger minimum size + size grip
      - Double-click to select
      - Keyboard shortcuts (Enter accepts, Esc cancels, Ctrl+F focuses search)
      - Persistent geometry/splitter state via QSettings
      - Optional 'Use as default' checkbox (exposed via use_as_default())
    """
    ORG = "WildGPT"
    APP = "WildGPT"

    def __init__(self, personalities: List[Dict[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Personality")
        self.setMinimumSize(800, 550)  # bigger default floor
        self.setSizeGripEnabled(True)  # allow drag-to-resize in the corner
        # Give the dialog full window controls (minimize, maximize, close)
        flags = self.windowFlags()
        flags |= Qt.WindowMinimizeButtonHint
        flags |= Qt.WindowMaximizeButtonHint
        flags |= Qt.WindowCloseButtonHint
        flags |= Qt.WindowSystemMenuHint  # (helps on Windows/Some WMs)
        self.setWindowFlags(flags)

        # Ditch the "What's This?" help button if it appears
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.selected_item: Optional[QListWidgetItem] = None
        self._personalities = personalities

        # ---------- Top controls ----------
        top = QWidget(self)
        top.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search personalities (name or content)…  ⌘")
        self.search.setClearButtonEnabled(True)
        top_layout.addWidget(QLabel("Find:"))
        top_layout.addWidget(self.search)

        # ---------- Splitter area ----------
        splitter = QSplitter(Qt.Horizontal, self)

        # Left: list
        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget(self)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setMinimumWidth(260)
        left_layout.addWidget(self.list_widget)

        self.count_label = QLabel("", self)
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_label.setStyleSheet("color: gray;")
        left_layout.addWidget(self.count_label)

        splitter.addWidget(left)

        # Right: preview tabs
        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget(self)
        # Overview tab
        self.overview_tab = QWidget(self)
        ov_layout = QVBoxLayout(self.overview_tab)
        ov_layout.setContentsMargins(8, 8, 8, 8)
        self.name_label = QLabel("<b>—</b>", self)
        self.name_label.setTextFormat(Qt.RichText)
        self.name_label.setWordWrap(True)
        self.meta_label = QLabel("", self)  # room for mini details if you add tags later
        self.meta_label.setStyleSheet("color: gray;")
        self.meta_label.setWordWrap(True)
        ov_layout.addWidget(self.name_label)
        ov_layout.addWidget(self.meta_label)
        ov_layout.addStretch(1)

        # Prompt tab
        self.prompt_view = QPlainTextEdit(self)
        self.prompt_view.setReadOnly(True)
        self.prompt_view.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.Monospace)
        self.prompt_view.setFont(mono)

        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.prompt_view, "Prompt")
        right_layout.addWidget(self.tabs)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ---------- Buttons ----------
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.ok_btn = buttons.button(QDialogButtonBox.Ok)
        self.cancel_btn = buttons.button(QDialogButtonBox.Cancel)

        self.default_checkbox = QCheckBox("Use this personality as default", self)  # todo currently not actually doing anything
        self.default_checkbox.setChecked(False)

        # ---------- Main layout ----------
        layout = QVBoxLayout(self)
        layout.addWidget(top)
        layout.addWidget(splitter)
        layout.addWidget(self.default_checkbox)
        layout.addWidget(buttons)

        # ---------- Wire up ----------
        self._populate_list(self._personalities)
        self._update_count()

        self.search.textChanged.connect(self._filter)
        self.list_widget.currentItemChanged.connect(self._update_preview)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.accept())
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Shortcuts-ish behavior
        self.search.returnPressed.connect(lambda: self.accept() if self.list_widget.currentItem() else None)
        self.search.installEventFilter(self)  # allow Esc to clear if needed

        # Persist window geometry & splitter
        self._settings = QSettings(self.ORG, self.APP)
        self._splitter = splitter
        self._restore_prefs()

        # Focus search on open (because yolo productivity)
        self.search.setFocus(Qt.TabFocusReason)

    # ---------- Public API ----------
    def get_selected(self) -> Optional[str]:
        """Backwards-compatible: returns the selected name or None."""
        item = self.list_widget.currentItem()
        return item.text() if item else None

    def get_selected_data(self) -> Optional[Dict]:
        """New hotness: returns the selected personality dict (name/content), or None."""
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    def use_as_default(self) -> bool:
        """Whether the 'Use as default' checkbox is ticked."""
        return self.default_checkbox.isChecked()

    # ---------- Internal helpers ----------
    def _populate_list(self, personalities: List[Dict[str, str]]) -> None:
        self.list_widget.clear()
        for p in personalities:
            name = p.get("name", "Unnamed")
            content = p.get("content", "")
            item = QListWidgetItem(name, self.list_widget)
            item.setData(Qt.UserRole, p)  # store the whole dict for later retrieval
            item.setToolTip(content if len(content) < 300 else content[:300] + "…")
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        else:
            self.name_label.setText("<b>—</b>")
            self.meta_label.setText("")
            self.prompt_view.setPlainText("")

    def _filter(self, text: str):
        text = (text or "").strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            data = item.data(Qt.UserRole) or {}
            haystack = f"{item.text()} {data.get('content','')}".lower()
            item.setHidden(text not in haystack)
        # After filtering, ensure something is selected if available
        visible_items = [self.list_widget.item(i)
                         for i in range(self.list_widget.count())
                         if not self.list_widget.item(i).isHidden()]
        if visible_items:
            self.list_widget.setCurrentItem(visible_items[0])
        else:
            self.name_label.setText("<b>—</b>")
            self.meta_label.setText("")
            self.prompt_view.setPlainText("")
        self._update_count()

    def _update_count(self):
        total = self.list_widget.count()
        visible = sum(0 if self.list_widget.item(i).isHidden() else 1 for i in range(total))
        self.count_label.setText(f"Showing {visible} of {total}")

    def _update_preview(self, current: QListWidgetItem, _prev: QListWidgetItem):
        if not current:
            return
        data = current.data(Qt.UserRole) or {}
        name = data.get("name", "Unnamed")
        content = data.get("content", "").strip()
        # A tiny “meta” line—tweak as you add fields (e.g., tags) later
        approx_len = f"~{len(content.split())} words" if content else ""
        self.name_label.setText(f"<b>{name}</b>")
        self.meta_label.setText(approx_len)
        self.prompt_view.setPlainText(content)

    # ---------- Persistence ----------
    def _restore_prefs(self):
        geo = self._settings.value("personalityPicker/geometry")
        split = self._settings.value("personalityPicker/splitter")
        if geo is not None:
            self.restoreGeometry(geo)
        if split is not None:
            try:
                self._splitter.restoreState(split)
            except Exception:
                pass

    def _save_prefs(self):
        self._settings.setValue("personalityPicker/geometry", self.saveGeometry())
        self._settings.setValue("personalityPicker/splitter", self._splitter.saveState())

    # ---------- Events ----------
    def eventFilter(self, obj, event):
        # Quick Esc behavior in the search field: clear if there’s text, otherwise let dialog handle Esc
        if obj is self.search and event.type() == event.KeyPress and event.key() == Qt.Key_Escape:
            if self.search.text():
                self.search.clear()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        # Ctrl+F focuses the search box. Enter accepts.
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_F:
            self.search.setFocus()
            self.search.selectAll()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.list_widget.currentItem():
                self.accept()
                return
        super().keyPressEvent(event)

    def accept(self):
        # Don’t accept if nothing is visible/selected
        if not self.list_widget.currentItem() or self.list_widget.currentItem().isHidden():
            return
        self._save_prefs()
        super().accept()

    def reject(self):
        self._save_prefs()
        super().reject()
