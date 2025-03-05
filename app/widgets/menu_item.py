from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QMouseEvent
from PyQt6.QtWidgets import QLabel, QCheckBox

from app.enums.annotation import VisibilityType
from app.objects import Annotation
from app.utils import pretty_text
from app.styles.style_sheets import LabelStyleSheet, CheckBoxStyleSheet

if TYPE_CHECKING:
    from app.canvas import Canvas

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
                 name: str = None
                 ) -> None:
        QLabel.__init__(self, text)
        ContextMenuItem.__init__(self)
        self.setAttribute(__background__)

        self.parent = parent
        self.risky = risky
        self.name = name

        self.on_left_click = binding
        self.on_right_click = binding

        self.setStyleSheet(str(LabelStyleSheet(risky)))


class ContextCheckBox(QCheckBox, ContextMenuItem):
    def __init__(self,
                 parent: 'Canvas',
                 annotation: Annotation
                 ) -> None:
        QCheckBox.__init__(self)
        ContextMenuItem.__init__(self)

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.parent = parent
        self.annotation = annotation

        self.update()

    def on_mouse_enter(self) -> None:
        self.annotation.highlighted = True
        self.parent.update()

    def on_mouse_leave(self) -> None:
        self.annotation.highlighted = False
        self.parent.update()

    def on_left_click(self) -> None:
        if self.annotation.selected:
            self.parent.unselect_annotation(self.annotation)
        else:
            self.parent.add_selected_annotation(self.annotation)

        self.update()
        self.parent.update()

    def on_right_click(self) -> None:
        shift_pressed = Qt.KeyboardModifier.ShiftModifier \
                        & QGuiApplication.keyboardModifiers()

        if self.annotation.visible == VisibilityType.VISIBLE:
            self.annotation.visible = VisibilityType.BOX_ONLY \
                if shift_pressed else VisibilityType.HIDDEN

        else:
            self.annotation.visible = VisibilityType.VISIBLE

        self.update()
        self.parent.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def update(self) -> None:
        self.setChecked(self.annotation.visible == VisibilityType.VISIBLE)
        self.setStyleSheet(str(CheckBoxStyleSheet(self.annotation)))
        self.setText(pretty_text(self.annotation.label_name))
