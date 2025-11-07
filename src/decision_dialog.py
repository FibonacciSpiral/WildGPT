from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

class DecisionDialog(QDialog):
    """
    Simple dialog with 3 buttons: Create, Edit, Delete.
    Disappears after selection and stores the chosen action.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Personality Editor")
        self.setMinimumWidth(300)
        self._action = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        layout.addWidget(QLabel("What would you like to do?", self, alignment=Qt.AlignCenter))

        # Button row
        btn_row = QHBoxLayout()
        self.create_btn = QPushButton("Create")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")

        for btn in (self.create_btn, self.edit_btn, self.delete_btn):
            btn.setMinimumWidth(80)
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        # Connect signals
        self.create_btn.clicked.connect(lambda: self._choose("create"))
        self.edit_btn.clicked.connect(lambda: self._choose("edit"))
        self.delete_btn.clicked.connect(lambda: self._choose("delete"))

    def _choose(self, action: str):
        """Store action, accept dialog."""
        self._action = action
        self.accept()

    def get_action(self) -> str:
        """Returns the user's selected action (create/edit/delete)."""
        return self._action
