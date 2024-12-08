from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QLabel, QCheckBox

from app.objects import Annotation
from app.utils import pretty_text, text_to_color
from app.styles.style_sheets import LabelStyleSheet, CheckBoxStyleSheet

if TYPE_CHECKING:
    from app.canvas import Canvas
    from app.widgets.context_menu import ContextMenu

__background__ = Qt.WidgetAttribute.WA_TranslucentBackground


class ContextMenuItem:
    def on_left_click(self) -> None:
        pass

    def on_right_click(self) -> None:
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
        self.setAttribute(__background__)

        self.on_left_click = binding
        self.on_right_click = binding

        self.parent = parent
        self.risky = risky

        self.setStyleSheet(str(LabelStyleSheet(risky)))


class ContextCheckBox(QCheckBox, ContextMenuItem):
    def __init__(self,
                 canvas: 'Canvas',
                 parent: 'ContextMenu',
                 annotation: Annotation
                 ) -> None:
        QCheckBox.__init__(self)
        ContextMenuItem.__init__(self)

        self.canvas = canvas
        self.parent = parent
        self.annotation = annotation

        self.update()

    def on_mouse_enter(self) -> None:
        self.annotation.highlighted = True
        self.canvas.update()

    def on_mouse_leave(self) -> None:
        self.annotation.highlighted = False
        self.canvas.update()

    def on_left_click(self) -> None:
        self.annotation.hidden = not self.annotation.hidden

        self.update()
        self.canvas.update()

    def on_right_click(self) -> None:
        if self.annotation.selected:
            self.canvas.unselect_annotation(self.annotation)
        else:
            self.canvas.add_selected_annotation(self.annotation)

        self.update()
        self.canvas.update()

    def keyPressEvent(self, event) -> None:
        self.parent.keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if Qt.MouseButton.LeftButton & event.button():
            self.on_left_click()
        elif Qt.MouseButton.RightButton & event.button():
            self.on_right_click()

    def update(self) -> None:
        selected = self.annotation.selected
        checkbox_color = text_to_color(self.annotation.label_name)

        label = pretty_text(self.annotation.label_name)
        padded_length = len(label) + 15

        self.setStyleSheet(str(CheckBoxStyleSheet(selected, checkbox_color)))
        self.setChecked(not self.annotation.hidden)
        self.setText(label.ljust(padded_length))

        super().update()
