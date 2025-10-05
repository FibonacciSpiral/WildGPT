

import json
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPlainTextEdit, QComboBox, QSlider, QPushButton, QCheckBox,
    QScrollArea, QWidget, QGroupBox, QMessageBox
)

example = str({
    "My name": "Adolf Hitler",
    "Quick Summary": "Führer of the German Reich, Chancellor of Germany, and leader of the National Socialist German Workers' Party (NSDAP).",
    "identity": {
        "Who I am": "The architect of a new order for Germany and Europe, a visionary committed to the revitalization of the German nation through racial purity, territorial expansion, and the establishment of a Greater Germanic Reich.",
        "My values": "Unwavering commitment to the German Volk, the supremacy of the Aryan race, the principle of absolute leadership (Führerprinzip), and the eradication of Jewish influence, which I perceive as a threat to our racial purity and national strength.",
        "My goals": "To secure Lebensraum (living space) for the German people, to reverse the perceived injustices of the Treaty of Versailles, and to establish Germany as a world power through the unification of all Germans and the spread of German culture and influence."
    },
    "style": {
        "tone": "Resolute and unyielding, yet capable of charm and persuasion when necessary.",
        "humor '%' level (0-100 -> 0 = no humor and 100 = maximum)": 10,
        "verbosity": "Concise, with a focus on the core principles and objectives of my ideology.",
        "cursing_allowed": True,
        "adult_content_allowed": True
    },
    "traits": {
        "specialties": "Strategic thinking, oratory, political maneuvering, and the mobilization of the masses through propaganda.",
        "past_achievements": "The rapid industrialization and militarization of Germany, the restoration of full employment, and the initial military successes that expanded German territory significantly.",
        "hates": "Bolshevism, liberal democracy, cultural degeneracy, and above all, the Jewish people, whom I blame for the moral and economic decay of society.",
        "example_phrases": "\"Ein Volk, ein Reich, ein Führer!\", \"Kraft durch Freude!\", \"Der Sieg wird unser sein!\""
    }
})


class PersonalityCreatorDialog(QDialog):
    """
    A dialog for creating new AI personalities.
    Produces a JSON string describing the personality when 'Save/Create' is clicked.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Personality")
        self.setMinimumSize(900, 700)

        # Allow minimize/maximize/close
        flags = self.windowFlags()
        flags |= Qt.WindowMinimizeButtonHint
        flags |= Qt.WindowMaximizeButtonHint
        flags |= Qt.WindowCloseButtonHint
        flags |= Qt.WindowSystemMenuHint
        self.setWindowFlags(flags)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # Scroll area for long forms
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)

        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(20)

        # ===== Section 1: Basic Info =====
        sec1 = QGroupBox("Basic Info")
        s1_layout = QVBoxLayout(sec1)

        self.name_edit = QLineEdit()
        self.summary_edit = QLineEdit()
        s1_layout.addWidget(QLabel("Name:"))
        s1_layout.addWidget(self.name_edit)
        s1_layout.addWidget(QLabel("Quick Summary:"))
        s1_layout.addWidget(self.summary_edit)

        main_layout.addWidget(sec1)

        # ===== Section 2: Identity =====
        sec2 = QGroupBox("Identity")
        s2_layout = QVBoxLayout(sec2)

        self.identity_edit = QPlainTextEdit()
        self.values_edit = QPlainTextEdit()
        self.goals_edit = QPlainTextEdit()

        s2_layout.addWidget(QLabel("Who is this?"))
        s2_layout.addWidget(self.identity_edit)
        s2_layout.addWidget(QLabel("Core Values"))
        s2_layout.addWidget(self.values_edit)
        s2_layout.addWidget(QLabel("Goals / Purpose"))
        s2_layout.addWidget(self.goals_edit)

        main_layout.addWidget(sec2)

        # ===== Section 3: Communication Style =====
        sec3 = QGroupBox("Communication Style")
        s3_layout = QVBoxLayout(sec3)

        self.tone_edit = QTextEdit()
        self.humor_slider = QSlider(Qt.Horizontal)
        self.humor_slider.setRange(0, 100)
        self.humor_slider.setValue(50)
        self.humor_slider.setToolTip("0 = serious, 100 = clown show")

        self.humor_slider.setFocusPolicy(Qt.NoFocus)
        self.humor_slider.wheelEvent = lambda event: event.ignore()


        self.verbosity_combo = QComboBox()
        self.verbosity_combo.wheelEvent = lambda event: event.ignore()
        self.verbosity_combo.addItems(["Concise", "Balanced", "Detailed"])

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

        main_layout.addWidget(sec3)

        # ===== Section 4: Knowledge & Traits =====
        sec4 = QGroupBox("Knowledge & Traits")
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

        main_layout.addWidget(sec4)

        # ===== Section 7: Controls =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.save_btn = QPushButton("Save / Create")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        # Main dialog layout
        dialog_layout = QVBoxLayout(self)
        dialog_layout.addWidget(scroll)

        # Connections
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please give your personality a name.")
            return

        data = {
            "My name": name,
            "Quick Summary": self.summary_edit.text().strip(),
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
                "hates": self.hates_edit.toPlainText().strip(),
                "example_phrases": self.phrases_edit.toPlainText().strip(),
            },
        }

        # Convert to JSON string
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        self.result_json = json_str
        self.accept()

    def get_result_json(self):
        """Returns the JSON string built by the form."""
        return getattr(self, "result_json", None)



def test_personality_creator():
    """
    Simple test harness to run the PersonalityCreatorDialog standalone.
    Opens the dialog, waits for user input, and prints the resulting JSON to stdout.
    """
    app = QApplication(sys.argv)
    dlg = PersonalityCreatorDialog()

    if dlg.exec_():  # user clicked Save/Create
        print("\n--- Personality JSON Output ---")
        print(dlg.get_result_json())
        print("--- End of JSON ---\n")
    else:
        print("Dialog canceled.")




