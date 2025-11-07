import json
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPlainTextEdit, QComboBox, QSlider, QPushButton, QCheckBox,
    QScrollArea, QWidget, QGroupBox, QMessageBox, QTabWidget, QSizePolicy
)


class PersonalityCreatorDialog(QDialog):
    """
    Hybrid personality editor with two modes:
      1) Structured Form (guided fields)
      2) Freeform Editor ("wordpad"-style)

    Produces a JSON string on Save. In Structured Form mode, it emits the
    detailed JSON schema; in Freeform mode, it emits {"name": str, "content": str}.
    Use get_result_json() after exec_() to retrieve the JSON string.
    """

    TAB_FORM = 0
    TAB_FREEFORM = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Personality")
        self.setMinimumSize(950, 740)

        # Allow minimize/maximize/close
        flags = self.windowFlags()
        flags |= Qt.WindowMinimizeButtonHint
        flags |= Qt.WindowMaximizeButtonHint
        flags |= Qt.WindowCloseButtonHint
        flags |= Qt.WindowSystemMenuHint
        self.setWindowFlags(flags)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # ===== Root layout (NO scroll here; buttons live outside tabs) =====
        root = QVBoxLayout(self)
        root.setSpacing(16)

        # ===== Tabs =====
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs)

        # Build both tabs
        self._build_form_tab()      # scroll lives INSIDE this tab only
        self._build_freeform_tab()  # editor already scrolls itself

        # ===== Fixed footer controls (outside tabs & outside any scroll) =====
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.copy_to_freeform_btn = QPushButton("Convert to Freeform")
        self.save_btn = QPushButton("Save / Create")
        self.cancel_btn = QPushButton("Cancel")
        footer.addWidget(self.copy_to_freeform_btn)
        footer.addWidget(self.save_btn)
        footer.addWidget(self.cancel_btn)
        root.addLayout(footer)

        # Connections
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)
        self.copy_to_freeform_btn.clicked.connect(self._populate_freeform_from_form)

        # Cross-tab name syncing (summary removed)
        self._link_line_edits(self.name_edit, self.freeform_name_edit)

    # ---------------------------------------------------------------------
    # UI Builders
    # ---------------------------------------------------------------------
    def _build_form_tab(self) -> None:
        # Put the long structured form inside a scroll area (tab content)
        form_content = QWidget()
        layout = QVBoxLayout(form_content)
        layout.setSpacing(20)

        # ===== Section 1: Basic Info =====
        sec1 = QGroupBox("Basic Info")
        s1_layout = QVBoxLayout(sec1)
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("The name of the personality.")
        s1_layout.addWidget(QLabel("Name:"))
        s1_layout.addWidget(self.name_edit)
        layout.addWidget(sec1)

        # ===== Section 2: Identity =====
        sec2 = QGroupBox("Identity")
        s2_layout = QVBoxLayout(sec2)
        self.identity_edit = QPlainTextEdit()
        self.identity_edit.setToolTip("Describe who this personality is.")
        self.values_edit = QPlainTextEdit()
        self.values_edit.setToolTip("Describe the core values of this personality.")
        self.goals_edit = QPlainTextEdit()
        self.goals_edit.setToolTip("Describe the goals or purpose of this personality.")
        s2_layout.addWidget(QLabel("Who is this?"))
        s2_layout.addWidget(self.identity_edit)
        s2_layout.addWidget(QLabel("Core Values"))
        s2_layout.addWidget(self.values_edit)
        s2_layout.addWidget(QLabel("Goals / Purpose"))
        s2_layout.addWidget(self.goals_edit)
        layout.addWidget(sec2)

        # ===== Section 3: Communication Style =====
        sec3 = QGroupBox("Communication Style")
        s3_layout = QVBoxLayout(sec3)
        self.tone_edit = QTextEdit()
        self.tone_edit.setPlaceholderText("E.g. Formal, casual, witty, sarcastic, poetic, etc.")
        self.tone_edit.setToolTip("Describe the tone or style of communication.")
        self.tone_edit.setAcceptRichText(False)

        self.humor_slider = QSlider(Qt.Horizontal)
        self.humor_slider.setRange(0, 100)
        self.humor_slider.setValue(50)
        self.humor_slider.setToolTip("0 = serious, 100 = maximum goofs")
        self.humor_slider.setFocusPolicy(Qt.NoFocus)
        self.humor_slider.wheelEvent = lambda event: event.ignore()

        self.verbosity_combo = QComboBox()
        self.verbosity_combo.wheelEvent = lambda event: event.ignore()
        self.verbosity_combo.addItems([
            "Hellen Keller", "Observing Mauna", "Concise", "Balanced",
            "Detailed", "Sesquipedalian", "Cruciverbal"
        ])

        self.cursing_check = QCheckBox("Cursing allowed")
        self.adult_check = QCheckBox("Adult content allowed")

        s3_layout.addWidget(QLabel("Tone"))
        s3_layout.addWidget(self.tone_edit)
        s3_layout.addWidget(QLabel("Humor level"))
        s3_layout.addWidget(self.humor_slider)
        s3_layout.addWidget(QLabel("Verbosity"))
        s3_layout.addWidget(self.verbosity_combo)
        s3_layout.addWidget(self.cursing_check)
        s3_layout.addWidget(self.adult_check)
        layout.addWidget(sec3)

        # ===== Section 4: Knowledge & Traits =====
        sec4 = QGroupBox("Knowledge and Traits")
        s4_layout = QVBoxLayout(sec4)
        self.specialties_edit = QPlainTextEdit()
        self.achievements_edit = QPlainTextEdit()
        self.likes_edit = QPlainTextEdit()
        self.hates_edit = QPlainTextEdit()
        self.phrases_edit = QPlainTextEdit()

        s4_layout.addWidget(QLabel("Specialties / Skills"))
        s4_layout.addWidget(self.specialties_edit)
        s4_layout.addWidget(QLabel("Past Achievements"))
        s4_layout.addWidget(self.achievements_edit)
        s4_layout.addWidget(QLabel("Things They Like"))
        s4_layout.addWidget(self.likes_edit)
        s4_layout.addWidget(QLabel("Things They Hate"))
        s4_layout.addWidget(self.hates_edit)
        s4_layout.addWidget(QLabel("Example Phrases / Catchphrases"))
        s4_layout.addWidget(self.phrases_edit)
        layout.addWidget(sec4)

        layout.addStretch(1)

        # Wrap in a scroll area for the tab
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setWidget(form_content)
        self.tabs.addTab(form_scroll, "Structured Form")

    def _build_freeform_tab(self) -> None:
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(12)

        # Minimal header (name only in freeform)
        header = QWidget(main_widget)
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        self.freeform_name_edit = QLineEdit()
        self.freeform_name_edit.setPlaceholderText("Personality name…")
        h.addWidget(QLabel("Name:"))
        h.addWidget(self.freeform_name_edit, 1)
        layout.addWidget(header)

        # Big editor (already scrollable)
        self.freeform_edit = QPlainTextEdit(main_widget)
        self.freeform_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.freeform_edit.setPlaceholderText(
            "Write anything you want here — a system prompt, persona definition, or creative blurb. "
            "Tip: You can also paste JSON {\"name\": ..., \"content\": ...} or a whole structured schema."
        )
        layout.addWidget(self.freeform_edit)

        self.tabs.addTab(main_widget, "Freeform Editor")

    # ---------------------------------------------------------------------
    # Helpers & Actions
    # ---------------------------------------------------------------------
    def _collect_form_data(self) -> dict:
        """Collects the structured form data into the schema dict."""
        name = self.name_edit.text().strip()
        data = {
            "My name": name,
            "identity": {
                "Who I am": self.identity_edit.toPlainText().strip(),
                "My values": self.values_edit.toPlainText().strip(),
                "My goals": self.goals_edit.toPlainText().strip(),
            },
            "style": {
                "tone": self.tone_edit.toPlainText().strip(),
                "humor '%' level (0-100 -> 0 = no humor and 100 = maximum)": self.humor_slider.value(),
                "verbosity": self.verbosity_combo.currentText().lower(),
                "cursing_allowed": self.cursing_check.isChecked(),
                "adult_content_allowed": self.adult_check.isChecked(),
            },
            "traits": {
                "specialties": self.specialties_edit.toPlainText().strip(),
                "past_achievements": self.achievements_edit.toPlainText().strip(),
                "likes": self.likes_edit.toPlainText().strip(),
                "hates": self.hates_edit.toPlainText().strip(),
                "example_phrases": self.phrases_edit.toPlainText().strip(),
            },
        }
        return data

    def _populate_freeform_from_form(self) -> None:
        """Converts the current structured form into JSON and moves to Freeform tab."""
        data = self._collect_form_data()
        try:
            pretty = json.dumps(data, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "JSON Error", f"Failed to serialize form to JSON:{e}")
            return
        self.freeform_edit.setPlainText(pretty)
        # Keep name visible in freeform header
        self.freeform_name_edit.setText(self.name_edit.text())
        self.tabs.setCurrentIndex(self.TAB_FREEFORM)

    def _link_line_edits(self, a: QLineEdit, b: QLineEdit) -> None:
        """Two-way sync between line edits without feedback loops."""
        def sync_a_to_b(text: str):
            if b.text() != text:
                b.blockSignals(True)
                b.setText(text)
                b.blockSignals(False)
        def sync_b_to_a(text: str):
            if a.text() != text:
                a.blockSignals(True)
                a.setText(text)
                a.blockSignals(False)
        a.textChanged.connect(sync_a_to_b)
        b.textChanged.connect(sync_b_to_a)

    # ---------------------------------------------------------------------
    # Save logic
    # ---------------------------------------------------------------------
    def _on_save(self):
        current = self.tabs.currentIndex()

        if current == self.TAB_FORM:
            # Structured form mode
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Missing Name", "Please give your personality a name.")
                return
            data = self._collect_form_data()
            try:
                json_str = json.dumps(data, indent=4, ensure_ascii=False)
            except Exception as e:
                QMessageBox.warning(self, "JSON Error", f"Could not serialize to JSON:{e}")
                return
        else:
            # Freeform mode
            name = self.freeform_name_edit.text().strip() or self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Missing Name", "Please add a name in the Freeform tab header.")
                return
            raw_text = self.freeform_edit.toPlainText().strip()
            if not raw_text:
                QMessageBox.warning(self, "Empty", "Please write something before saving.")
                return
            data = {"name": name, "content": raw_text}
            try:
                json_str = json.dumps(data, indent=4, ensure_ascii=False)
            except Exception as e:
                QMessageBox.warning(self, "JSON Error", f"Could not serialize to JSON:{e}")
                return

        self.result_json = json_str
        self.accept()

    def get_result_json(self):
        """Returns the JSON string built by the editor."""
        return getattr(self, "result_json", None)


# -------------------------------------------------------------------------
# Standalone test harness
# -------------------------------------------------------------------------

def test_personality_creator():
    """
    Simple test harness to run the PersonalityCreatorDialog standalone.
    Opens the dialog, waits for user input, and prints the resulting JSON to stdout.
    """
    app = QApplication(sys.argv)
    dlg = PersonalityCreatorDialog()

    if dlg.exec_():  # user clicked Save/Create
        print("--- Personality JSON Output ---")
        print(dlg.get_result_json())
        print("--- End of JSON ---")
    else:
        print("Dialog canceled.")



#test_personality_creator()
