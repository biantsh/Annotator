import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QPixmap, QMouseEvent, QHideEvent, QShowEvent
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel

if TYPE_CHECKING:
    from app.canvas import Canvas

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')

__smooth_transform__ = Qt.TransformationMode.SmoothTransformation


class InvalidImageBanner(QWidget):
    icon_name = 'robo_bear_monitor.png'
    message = 'Couldn\'t open this one. It\'s likely unreadable or corrupted.'

    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent)
        self.parent = parent

        pixmap = QPixmap(os.path.join(__iconpath__, self.icon_name)).scaled(
            140, 214, transformMode=__smooth_transform__)

        icon_label = QLabel()
        icon_label.setPixmap(pixmap)

        message_label = QLabel(self.message)

        self.image_label = QLabel()
        self.image_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)

        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addStretch()
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        layout.addWidget(self.image_label)
        layout.addStretch()

        self.setLayout(layout)
        self.setMouseTracking(True)
        icon_label.setContentsMargins(0, 0, 0, 12)

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
