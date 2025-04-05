from typing import TYPE_CHECKING, Callable

from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QMenu, QHBoxLayout, QWidgetAction, QWidget, QLabel

from app.enums.annotation import VisibilityType
from app.objects import Annotation
from app.styles.style_sheets import LabelStyleSheet

if TYPE_CHECKING:
    from app.canvas import Canvas


class ContextButton(QLabel):
    def __init__(self, binding: Callable, text: str, risky: bool) -> None:
        super().__init__(text)

        self.on_left_click = binding
        self.on_right_click = binding
        self.risky = risky

        self.setStyleSheet(str(LabelStyleSheet(risky)))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


class ContextMenu(QMenu):
    background_color = 'rgba(33, 33, 33, 0.75)'
    hover_color = 'rgba(53, 53, 53, 0.75)'

    def __init__(self, parent: 'Canvas', annotation: Annotation) -> None:
        super().__init__(parent)

        self.parent = parent
        self.widgets = []

        def _hide_annotation() -> None:
            parent.hide_annotations(VisibilityType.HIDDEN)
            parent.unselect_all()

        buttons = [ContextButton(parent.copy_annotations, 'Copy', False),
                   ContextButton(parent.rename_annotations, 'Rename', False),
                   ContextButton(_hide_annotation, 'Hide', False)]

        if annotation.has_keypoints and annotation.label_schema.kpt_symmetry:
            buttons.append(ContextButton(parent.flip_keypoints, 'Flip', False))

        [self._add_item(button) for button in buttons]
        self.addSeparator()

        delete = ContextButton(parent.delete_annotations, 'Delete', True)
        self._add_item(delete)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _add_item(self, item: ContextButton) -> None:
        """Wrap the item inside a WidgetAction and add it to the menu."""
        widget = QWidget()
        widget.installEventFilter(self)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover)
        widget.setStyleSheet(f'background-color: {self.background_color}')

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 6, 0, 6)
        layout.addWidget(item)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(widget)

        self.addAction(widget_action)
        self.widgets.append(widget)

    def on_mouse_click(self, source: QObject, event: QEvent) -> None:
        if Qt.MouseButton.LeftButton & event.button():
            source.findChild(QLabel).on_left_click()

        elif Qt.MouseButton.RightButton & event.button():
            source.findChild(QLabel).on_right_click()

        self.close()

    def on_mouse_enter(self, source: QObject, event: QEvent) -> None:
        # Prevent triggering outside the widget on Linux
        if event.position().x() < 0 or event.position().y() < 0:
            return

        for widget in self.widgets:
            widget.setStyleSheet(f'background-color: {self.background_color};')

        source.setStyleSheet(f'background-color: {self.hover_color};')

    def on_mouse_leave(self, source: QObject) -> None:
        source.setStyleSheet(f'background-color: {self.background_color};')

    def showEvent(self, event: QShowEvent) -> None:
        self.parent.update_cursor_icon(Qt.CursorShape.ArrowCursor)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type == event.Type.MouseButtonPress:
            self.on_mouse_click(source, event)

        elif event_type == event.Type.HoverMove:
            self.on_mouse_enter(source, event)

        elif event_type == event.Type.HoverLeave:
            self.on_mouse_leave(source)

        return True
