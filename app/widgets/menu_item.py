from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QLabel, QCheckBox

from app.objects import Annotation
from app.utils import pretty_text, text_to_color
from app.styles.style_sheets import LabelStyleSheet, CheckBoxStyleSheet

if TYPE_CHECKING:
    from app.canvas import Canvas


class ContextMenuItem:
    def on_mouse_click(self) -> None:
        pass

    def on_mouse_enter(self) -> None:
        pass

    def on_mouse_leave(self) -> None:
        pass


class ContextButton(QLabel, ContextMenuItem):
    def __init__(self,
                 parent: 'Canvas',
                 binding: Callable,
                 text: str,
                 risky: bool,
                 ) -> None:
        QLabel.__init__(self, text)
        ContextMenuItem.__init__(self)

        self.on_mouse_click = binding
        self.parent = parent
        self.risky = risky

        self.setStyleSheet(str(LabelStyleSheet(risky)))


class ContextCheckBox(QCheckBox, ContextMenuItem):
    def __init__(self, parent: 'Canvas', annotation: Annotation) -> None:
        QCheckBox.__init__(self)
        ContextMenuItem.__init__(self)

        self.parent = parent
        self.annotation = annotation

        self.setChecked(not self.annotation.hidden)

        label = pretty_text(self.annotation.label_name)
        padded_length = len(label) + 15

        self.setText(label.ljust(padded_length))
        checkbox_color = text_to_color(self.annotation.label_name)

        self.setStyleSheet(str(CheckBoxStyleSheet(checkbox_color)))

    def on_mouse_enter(self) -> None:
        self.annotation.highlighted = True
        self.parent.update()

    def on_mouse_leave(self) -> None:
        self.annotation.highlighted = False
        self.parent.update()

    def on_mouse_click(self) -> None:
        self.annotation.hidden = not self.annotation.hidden
        self.setChecked(not self.annotation.hidden)

        self.parent.update()

    def mousePressEvent(self, event: QEvent) -> None:
        self.on_mouse_click()
