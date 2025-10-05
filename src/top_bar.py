from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QPushButton,
    QSpacerItem, QWidget, QLabel, QSizePolicy
)

class TopBar(QWidget):
    modelChanged = pyqtSignal(str)
    settingsChanged = pyqtSignal(dict)
    saveChatRequested = pyqtSignal()
    loadChatRequested = pyqtSignal()
    pickPersonalityRequested = pyqtSignal()
    createPersonalityRequested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)

        # Model selector
        self.model_combo = QComboBox(self)
        self.model_combo.setEditable(False)
        self.model_combo.setInsertPolicy(QComboBox.NoInsert)
        self.model_combo.addItems([
            "alpindale/WizardLM-2-8x22B",
            "zetasepic/Qwen2.5-72B-Instruct-abliterated",
            "zetasepic/Qwen2.5-72B-Instruct-abliterated-v2",
            "huihui-ai/Qwen2.5-72B-Instruct-abliterated",
            "huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated",
            "failspy/llama-3-70B-Instruct-abliterated",
            "failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5",
            "failspy/Llama-3-70B-Instruct-abliterated-v3",
            "failspy/Smaug-Llama-3-70B-Instruct-abliterated-v3",
            "crestf411/L3-70B-daybreak-abliterated-v0.4",
            "nvidia/Llama3-ChatQA-1.5-70B",
            "NousResearch/Hermes-2-Theta-Llama-3-70B",
            "m42-health/Llama3-Med42-70B",
            "Dogge/llama-3-70B-uncensored",
            "theo77186/Llama-3-70B-Instruct-norefusal",
            "KaraKaraWitch/Llama-3.3-MagicalGirl-2",
            "google/gemma-3-27b-it"
        ])
        self.model_combo.setCurrentIndex(0)

        self.model_combo.view().setMouseTracking(True)

        # Temperature only (Max tokens removed)
        self.temp_spin = QDoubleSpinBox(self)
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setDecimals(2)
        self.temp_spin.setMinimumWidth(140)

        # Action buttons
        self.save_chat_btn = QPushButton("Save Chat", self)
        self.load_chat_btn = QPushButton("Load Chat", self)
        self.pick_persona_btn = QPushButton("Pick Personality", self)
        self.create_persona_btn = QPushButton("Create Personality", self)

        # Layout row
        layout.addWidget(QLabel("Model:"), 0, 0)
        layout.addWidget(self.model_combo, 0, 1)
        layout.addWidget(QLabel("Temperature:"), 0, 2)
        layout.addWidget(self.temp_spin, 0, 3)
        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 4)
        layout.addWidget(self.save_chat_btn, 0, 5)
        layout.addWidget(self.load_chat_btn, 0, 6)
        layout.addWidget(self.pick_persona_btn, 0, 7)
        layout.addWidget(self.create_persona_btn, 0, 8)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(4, 1)
        self._equalize_topbar_buttons()

        # Signals
        self.model_combo.currentTextChanged.connect(self.modelChanged.emit)
        self.temp_spin.valueChanged.connect(lambda _=None: self._emit_settings())
        self.save_chat_btn.clicked.connect(self.saveChatRequested)
        self.load_chat_btn.clicked.connect(self.loadChatRequested)
        self.pick_persona_btn.clicked.connect(self.pickPersonalityRequested)
        self.create_persona_btn.clicked.connect(self.createPersonalityRequested)

    def _emit_settings(self) -> None:
        self.settingsChanged.emit({"temperature": float(self.temp_spin.value())})

    def _equalize_topbar_buttons(self) -> None:
        btns = [self.save_chat_btn, self.load_chat_btn, self.pick_persona_btn, self.create_persona_btn]
        # Fix horizontal size so layout won't stretch them unevenly
        for b in btns:
            b.setSizePolicy(QSizePolicy.Fixed, b.sizePolicy().verticalPolicy())
        self.ensurePolished()  # ensures correct sizeHint with current style/font
        w = max(b.sizeHint().width() for b in btns)
        for b in btns:
            b.setFixedWidth(w + 100)

    def set_busy(self, busy):
        self.save_chat_btn.setEnabled(not busy)
        self.load_chat_btn.setEnabled(not busy)
        self.pick_persona_btn.setEnabled(not busy)
        self.create_persona_btn.setEnabled(not busy)
        self.model_combo.setEnabled(not busy)
        self.temp_spin.setEnabled(not busy)