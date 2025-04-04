from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QGuiApplication,
    QFontMetrics,
    QResizeEvent,
    QMouseEvent
)
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QStyleOptionButton,
    QStyle,
    QLabel,
    QCheckBox
)

from app.enums.annotation import VisibilityType
from app.styles.style_sheets import LabelStyleSheet, CheckBoxStyleSheet
from app.utils import pretty_text

if TYPE_CHECKING:
    from app.canvas import Canvas
    from app.objects import Annotation


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
        super().__init__(text)

        self.parent = parent
        self.risky = risky
        self.name = name

        self.on_left_click = binding
        self.on_right_click = binding

        self.setStyleSheet(str(LabelStyleSheet(risky)))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


class ContextCheckBox(QCheckBox, ContextMenuItem):
    def __init__(self, parent: 'Canvas', annotation: 'Annotation') -> None:
        super().__init__()

        self.parent = parent
        self.annotation = annotation
        self.is_elided = False

        self.setChecked(True)
        self.update()

    def _elide_text(self, text: str) -> str:
        option = QStyleOptionButton()
        option.rect = self.contentsRect()

        text_rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxContents, option, self)

        return QFontMetrics(self.font()).elidedText(
            text, Qt.TextElideMode.ElideRight, text_rect.width())

    def set_hidden(self, hidden: bool) -> None:
        fade_effect = QGraphicsOpacityEffect()
        fade_effect.setOpacity(0.6)

        self.setGraphicsEffect(fade_effect if hidden else None)
        self.setEnabled(not hidden)

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
            self.annotation.visible = VisibilityType.HIDDEN

            if shift_pressed and self.annotation.has_bbox:
                self.annotation.visible = VisibilityType.BOX_ONLY

        else:
            self.annotation.visible = VisibilityType.VISIBLE

        self.update()
        self.parent.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        base_text = pretty_text(self.annotation.label_name)
        elided_text = self._elide_text(base_text)

        self.is_elided = base_text != elided_text
        self.setText(elided_text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def update(self) -> None:
        self.setStyleSheet(str(CheckBoxStyleSheet(self.annotation)))
