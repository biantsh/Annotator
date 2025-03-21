from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QMouseEvent, QHideEvent, QShowEvent
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel

if TYPE_CHECKING:
    from app.canvas import Canvas


class InvalidImageLabel(QWidget):
    message = 'Couldn\'t open this one. It\'s likely unreadable or corrupted.'

    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent)
        self.parent = parent

        self.message_label = QLabel(self.message)
        self.image_label = QLabel()

        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addStretch()
        layout.addWidget(self.message_label)
        layout.addWidget(self.image_label)
        layout.addStretch()

        self.setLayout(layout)
        self.setMouseTracking(True)

    @property
    def controlled_actions(self) -> list[QAction]:
        return self.parent.actions() + \
            [action for action in self.parent.parent.actions()
             if action.text() in {'Box', 'Points'}]

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.parent.mouseMoveEvent(event)
        super().mouseMoveEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        for action in self.controlled_actions:
            action.setEnabled(True)

    def showEvent(self, event: QShowEvent) -> None:
        for action in self.controlled_actions:
            action.setEnabled(False)

        self.image_label.setText(self.parent.image_name)
