from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QCheckBox

from app.objects import Annotation
from app.utils import pretty_text, text_to_color
from app.styles.style_sheets import CheckBoxStyleSheet

if TYPE_CHECKING:
    from app.canvas import Canvas


class AnnoCheckBox(QCheckBox):
    def __init__(self,
                 parent: 'Canvas',
                 annotation: Annotation,
                 background_color: str
                 ) -> None:
        super().__init__()

        self.parent = parent
        self.annotation = annotation

        self.setChecked(not self.annotation.hidden)
        self.stateChanged.connect(self.flip_hidden)

        label = pretty_text(self.annotation.label_name)
        padded_length = len(label) + 15

        self.setText(label.ljust(padded_length))
        checkbox_color = text_to_color(self.annotation.label_name)

        self.setStyleSheet(str(CheckBoxStyleSheet(
            checkbox_color, background_color)))

    def flip_hidden(self) -> None:
        self.annotation.hidden = not self.annotation.hidden
        self.parent.update()

    def enterEvent(self, event: QEvent):
        self.annotation.highlighted = True
        self.parent.update()

    def leaveEvent(self, event: QEvent) -> None:
        self.annotation.highlighted = False
        self.parent.update()

    def mouseMoveEvent(self, event: QEvent) -> None:
        # Sometimes EnterEvent is missed
        self.enterEvent(event)
