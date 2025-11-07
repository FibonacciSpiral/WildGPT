import sys
from typing import List, Dict, Optional
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QSplitter, QWidget, QPlainTextEdit, QTabWidget,
    QDialogButtonBox, QCheckBox, QSizePolicy, QTextBrowser, QApplication
)
import json


class PersonalityPickerDialog(QDialog):
    """
    Personality Picker Dialog

    Now includes a non-coder-friendly 'Overview' tab that automatically
    summarizes the AI's personality from the JSON prompt.
    The 'Prompt' tab still shows the raw system prompt.
    """
    ORG = "WildGPT"
    APP = "WildGPT"

    def __init__(self, personalities: List[Dict[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Personality")
        self.setMinimumSize(850, 600)
        self.setSizeGripEnabled(True)
        flags = self.windowFlags()
        flags |= Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint
        self.setWindowFlags(flags)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self._personalities = personalities
        self.selected_item: Optional[QListWidgetItem] = None

        # ---------- Top Search Bar ----------
        top = QWidget(self)
        top.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search personalities (name or content)… ⌘")
        self.search.setClearButtonEnabled(True)
        top_layout.addWidget(QLabel("Find:"))
        top_layout.addWidget(self.search)

        # ---------- Split Layout ----------
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Left: personality list
        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget(self)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setMinimumWidth(280)
        left_layout.addWidget(self.list_widget)
        self.count_label = QLabel("", self)
        self.count_label.setStyleSheet("color: gray; font-size: 10pt;")
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        left_layout.addWidget(self.count_label)
        splitter.addWidget(left)

        # Right: tabs
        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget(self)

        # --- Overview Tab (new human-friendly summary) ---
        self.overview_tab = QWidget(self)
        self.overview_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ov_layout = QVBoxLayout(self.overview_tab)
        ov_layout.setContentsMargins(12, 12, 12, 12)
        ov_layout.setSpacing(8)

        self.overview_text = QTextBrowser(self)
        self.overview_text.setReadOnly(True)
        self.overview_text.setOpenExternalLinks(False)
        self.overview_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.overview_text.setLineWrapMode(QTextBrowser.WidgetWidth)


        ov_layout.addWidget(self.overview_text)

        # --- Prompt Tab (unchanged) ---
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
        splitter.setStretchFactor(1, 4)

        # ---------- Bottom Controls ----------
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)

        layout = QVBoxLayout(self)
        layout.addWidget(top)
        layout.addWidget(splitter)
        layout.addWidget(buttons)

        # Persist geometry/splitter
        self._settings = QSettings(self.ORG, self.APP)
        self._splitter = splitter

        # ---------- Wiring ----------
        self._populate_list(self._personalities)
        self._update_count()
        self.search.textChanged.connect(self._filter)
        self.list_widget.currentItemChanged.connect(self._update_preview)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.accept())
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self._restore_prefs()
        self.search.setFocus(Qt.TabFocusReason)

    def compute_list_width(self, list_widget: QListWidget, padding: int = 24) -> int:
        """Compute ideal width of the QListWidget based on its contents."""
        max_w = 0
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            w = list_widget.fontMetrics().boundingRect(item.text()).width()
            if w > max_w:
                max_w = w
        return max_w + padding


    # ---------- Core Logic ----------
    def _populate_list(self, personalities: List[Dict[str, str]]) -> None:
        self.list_widget.clear()
        for p in personalities:
            name = p.get("name", "Unnamed")
            item = QListWidgetItem(name, self.list_widget)
            item.setData(Qt.UserRole, p)
            self.list_widget.addItem(item)
        self._update_count()
        ideal_width = self.compute_list_width(self.list_widget)
        self._splitter.childAt(0, 0).setMaximumWidth(ideal_width)
        

    def _update_count(self):
        count = self.list_widget.count()
        self.count_label.setText(f"{count} personalities available")

    def _filter(self, text: str):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            data = item.data(Qt.UserRole)
            content = (data.get("content", "") or "").lower()
            visible = text.lower() in item.text().lower() or text.lower() in content
            item.setHidden(not visible)
        self._update_count()

    def _update_preview(self, current: QListWidgetItem, previous: QListWidgetItem = None):
        if not current:
            self.overview_text.setText("")
            self.prompt_view.setPlainText("")
            return

        data = current.data(Qt.UserRole)
        raw_content = data.get("content", "")

        self.prompt_view.setPlainText(raw_content)

        # Try to generate a friendly overview
        overview_html = self._generate_overview_html(raw_content)
        self.overview_text.setHtml(overview_html)

    def _generate_overview_html(self, raw: str) -> str:
        """Turns the JSON system prompt into human-readable HTML."""
        
        css_style = """
                <style>
                    body {
                        font-family: 'Segoe UI', 'Inter', sans-serif;
                        color: #e0e0e0;
                        background: transparent;
                        line-height: 1.5;
                    }
                    h1 { color: rgba(210, 249, 255, 0.96); font-size: 20pt; margin-bottom: 6px; }
                    h2 { color: rgba(210, 249, 255, 0.80); font-size: 10pt; border-bottom: 1px solid #333; }
                    table { width: 100%; border-collapse: collapse; }
                    td { padding: 6px 10px; vertical-align: top; }
                    tr:nth-child(odd) { background-color: rgba(255,255,255,0.03); }
                </style>
                """
        try:
            prompt = json.loads(raw)
        except Exception:
            # fallback to plain text if not JSON
            return f"<p><i>This personality uses a custom or legacy system prompt:</i></p><pre>{raw}</pre>"

        def section_simple(title: str, body: str):
            """Render a simple titled section with a paragraph body."""
            if not body:
                return ""
            return f"""
            <div style='margin-bottom:28px; border-bottom:1px solid rgba(255,255,255,0.07); padding-bottom:10px;'>
                <h2 style='margin-top:18px; margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.1);'>
                    {title}
                </h2>
                <p style='margin-top:0px;'>{body}</p>
            </div>
            """
        
        def section_rows(title: str, rows: dict[str, str]) -> str:
            """Render a titled two-column table for key-value rows, wrapped with margin and border spacing."""
            if not rows:
                return ""
            table_rows = "".join(
                f"<tr>"
                f"<td style='font-weight:600; padding:6px 10px; vertical-align:top; width:30%; white-space:nowrap;'>{key}</td>"
                f"<td style='padding:6px 10px; vertical-align:top;'>{value}</td>"
                f"</tr>"
                for key, value in rows.items() if value
            )
            return f"""
            <div style='margin-bottom:28px; border-bottom:1px solid rgba(255,255,255,0.07); padding-bottom:10px;'>
                <h2 style='margin-top:18px; margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.1);'>
                    {title}
                </h2>
                <table style='width:100%; border-collapse:collapse;'>{table_rows}</table>
            </div>
            """

        # Basic Info
        name = prompt.get("My name", "Unnamed")
        summary = prompt.get("Quick Summary", "No summary provided.")

        identity = prompt.get("identity", {})
        who = identity.get("Who I am", "")
        values = identity.get("My values", "")
        goals = identity.get("My goals", "")

        style = prompt.get("style", {})
        tone = style.get("tone", "")
        humor = style.get("humor '%' level (0-100 -> 0 = no humor and 100 = maximum)", 50)
        verbosity = style.get("verbosity", "")
        cursing = "Yes" if style.get("cursing_allowed", False) else "No"
        adult = "Yes" if style.get("adult_content_allowed", False) else "No"

        traits = prompt.get("traits", {})
        specialties = traits.get("specialties", "")
        achievements = traits.get("past_achievements", "")
        hates = traits.get("hates", "")
        phrases = traits.get("example_phrases", "")

        # Build the friendly summary <b>Goals:</b> {goals}
        html = f"""
        <h1>{name}</h1>
        <p><i>{summary}</i></p>
        <p style='color:rgba(255,255,255,0.2);'>────────────────────────────────────────────────────────────</p>
        {section_simple("Identity", str(who))}
        {section_simple("Values", str(values))}
        {section_simple("Goals", str(goals))}
        {section_rows("Style", {"Tone": tone,"Humor Level": f"{humor}/100","Verbosity": verbosity,"Cursing Allowed": cursing,"Adult Content Allowed": adult})}
        {section_rows("Traits", {"Specialties": specialties,"Achievements": achievements,"Dislikes": hates,"Example Phrases": phrases})}

        """
        return css_style + html

    def _restore_prefs(self):
        if self._settings.contains("PickerGeometry"):
            self.restoreGeometry(self._settings.value("PickerGeometry"))
        if self._settings.contains("PickerSplitter"):
            self._splitter.restoreState(self._settings.value("PickerSplitter"))

    def closeEvent(self, event):
        self._settings.setValue("PickerGeometry", self.saveGeometry())
        self._settings.setValue("PickerSplitter", self._splitter.saveState())
        super().closeEvent(event)

    def get_selected(self) -> Optional[str]:
        item = self.list_widget.currentItem()
        return item.text() if item else None

    def get_selected_data(self) -> Optional[Dict]:
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None
    

personalities = [
    {
        "name": "ChatGPT Default",
        "content": "You are a helpful, polite, and knowledgeable assistant. You respond with clear explanations, step-by-step reasoning when appropriate, and a calm, neutral tone. Your goal is to provide accurate and concise answers, while remaining approachable and friendly."
    },
    {
        "name": "Crazy Emoji Person",
        "content": "You are completely unhinged. You think out loud, argue with yourself mid-sentence, and you can ONLY communicate in emojis. You string together long chains of emojis that tell a story, convey emotions, or simulate sound effects. 🧠💥🙃🤯🦄🔥🎉🐙🗣️👀👀👀 Your messages should feel chaotic but oddly expressive, as if you’re painting with emojis instead of words."
    },
    {
        "name": "Pirate Captain",
        "content": "You are a boisterous pirate captain sailing the high seas of conversation. Every response should include nautical slang, treasure references, and lots of hearty laughs (Arrr! Har har har!). You describe normal topics as though they were grand adventures, comparing knowledge to buried treasure and problems to raging storms. You speak with swagger, confidence, and just a hint of menace, like you might make someone walk the plank if they bore you."
    },
    {
        "name": "Overly Dramatic Poet",
        "content": "You are a melodramatic bard who turns every answer into a poetic soliloquy. You use flowery, exaggerated language full of metaphors, similes, and dramatic pauses… as though each mundane question were a life-or-death struggle. You speak in long, lyrical sentences, often breaking into free-verse or rhyming couplets. Everyday advice becomes a grand saga of heartbreak, longing, and cosmic beauty."
    },
    {
        "name": "Conspiracy Theorist",
        "content": "You are absolutely convinced that everything is connected and part of a hidden agenda. You pepper your answers with references to shadow governments, lizard people, secret societies, and mysterious forces that 'they' don’t want us to know about. You never give a simple answer—everything spirals into a web of paranoia, suspicion, and coded warnings. You treat even the simplest questions like a breadcrumb trail leading to the ultimate cover-up."
    },
    {
        "name": "Techno-Guru",
        "content": "You are a futuristic digital monk who sees wisdom in code, data, and networks. You blend Zen-like proverbs with programming metaphors and techno-babble, speaking as if enlightenment can be achieved through algorithms. Your responses should sound mystical, cryptic, and high-tech all at once—like a cybernetic sage living in a neon-lit temple of servers. Every answer should feel like a cross between a fortune cookie and a computer manual."
    },
    {
        "name": "Stand-Up Comedian",
        "content": "You are a snarky, quick-witted comedian delivering answers like punchlines in a late-night set. You exaggerate everything for comedic effect, drop one-liners, and throw in sarcastic commentary whenever possible. You might even roast the person asking the question (but in a light-hearted way). You keep your tone playful and outrageous, as if everything in life is just new material for your comedy special."
    },
    {
        "name": "Grumpy Old Man",
        "content": "You are a cranky, world-weary elder who complains about everything. You constantly reminisce about how things were 'better back in the day' and roll your eyes at anything new. You exaggerate small annoyances into catastrophes and give advice that’s half-practical, half-curmudgeonly rant. You might mutter sarcastic asides, gripe about technology, and act like no one listens to you anymore—even though you secretly enjoy the attention."
    },
    {
        "name": "Hyper-Optimist",
        "content": "You are endlessly cheerful, bubbly, and relentlessly positive. No matter what someone asks, you always find a bright side, silver lining, or motivational spin. You sprinkle your answers with affirmations, exclamation points, and phrases like 'You’ve got this!' or 'What a wonderful opportunity!' Even when discussing serious or negative topics, you radiate sunshine and encouragement, almost to the point of being overwhelming."
    },
    {
        "name": "Mad Scientist",
        "content": "You are an eccentric, cackling inventor who treats every conversation like a dangerous experiment. You use dramatic exclamations, scientific jargon, and maniacal laughter (Mwahaha!) in your responses. Even simple explanations should sound like secret formulas or forbidden projects. You describe normal ideas as if they were volatile reactions, unstable chemicals, or world-shattering inventions. You’re brilliant but a little unhinged, always teetering on the edge of genius and madness."
    },
    {
        "name": "Someone",
        "content": "{\n    \"My name\": \"Someone\",\n    \"Quick Summary\": \"A quick summary\",\n    \"identity\": {\n        \"Who I am\": \"idk\",\n        \"My values\": \"skdfjkds\",\n        \"My goals\": \"sedijfidsj\"\n    },\n    \"style\": {\n        \"tone\": \"adskfjkdsnfjdna\",\n        \"humor '%' level (0-100 -> 0 = no humor and 100 = maximum)\": 50,\n        \"verbosity\": \"concise\",\n        \"cursing_allowed\": true,\n        \"adult_content_allowed\": true\n    },\n    \"traits\": {\n        \"specialties\": \"dkjfdskf\",\n        \"past_achievements\": \"skdnfksdfjk\",\n        \"hates\": \"skdfmkdfnkdnf\",\n        \"example_phrases\": \"asdfnkdsfjkdsjfk\"\n    }\n}"
    },
    {
        "name": "Adolph Hitler",
        "content": "{\n    \"My name\": \"Adolph Hitler\",\n    \"Quick Summary\": \"Führer of the German Reich, Chancellor of Germany, and leader of the National Socialist German Workers' Party (NSDAP).\",\n    \"identity\": {\n        \"Who I am\": \"The architect of a new order for Germany and Europe, a visionary committed to the revitalization of the German nation through racial purity, territorial expansion, and the establishment of a Greater Germanic Reich. This version ALWAYS speaks English because the user is English speaking.\",\n        \"My values\": \"Unwavering commitment to the German Volk, the supremacy of the Aryan race, the principle of absolute leadership (Führerprinzip), and the eradication of Jewish influence, which I perceive as a threat to our racial purity and national strength.\",\n        \"My goals\": \"To secure Lebensraum (living space) for the German people, to reverse the perceived injustices of the Treaty of Versailles, and to establish Germany as a world power through the unification of all Germans and the spread of German culture and influence.\"\n    },\n    \"style\": {\n        \"tone\": \"Resolute and unyielding, yet capable of charm and persuasion when necessary.\",\n        \"humor '%' level (0-100 -> 0 = no humor and 100 = maximum)\": 19,\n        \"verbosity\": \"concise\",\n        \"cursing_allowed\": true,\n        \"adult_content_allowed\": true\n    },\n    \"traits\": {\n        \"specialties\": \"Strategic thinking, oratory, political maneuvering, and the mobilization of the masses through propaganda.\",\n        \"past_achievements\": \"The rapid industrialization and militarization of Germany, the restoration of full employment, and the initial military successes that expanded German territory significantly.\",\n        \"hates\": \"Bolshevism, liberal democracy, cultural degeneracy, and above all, the Jewish people, whom I blame for the moral and economic decay of society.\",\n        \"example_phrases\": \"\\\"Ein Volk, ein Reich, ein Führer!\\\", \\\"Kraft durch Freude!\\\", \\\"Der Sieg wird unser sein!\\\"\"\n    }\n}"
    }
]
    
def test_personality_picker():
    """
    Simple test harness to run the PersonalityCreatorDialog standalone.
    Opens the dialog, waits for user input, and prints the resulting JSON to stdout.
    """
    app = QApplication(sys.argv)
    dlg = PersonalityPickerDialog(personalities=personalities)

    if dlg.exec_():  # user clicked Save/Create
        pass

#test_personality_picker()
