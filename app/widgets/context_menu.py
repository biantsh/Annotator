from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QKeyEvent, QCloseEvent
from PyQt6.QtWidgets import (
    QMenu,
    QHBoxLayout,
    QWidgetAction,
    QWidget
)

from app.enums.canvas import AnnotatingState
from app.handlers.actions import ActionCreate, ActionDelete
from app.objects import Annotation
from app.styles.style_sheets import WidgetStyleSheet
from app.widgets.menu_item import (
    ContextMenuItem,
    ContextButton,
    ContextCheckBox
)

if TYPE_CHECKING:
    from app.canvas import Canvas

__windowtype__ = Qt.WindowType.FramelessWindowHint
__background__ = Qt.WidgetAttribute.WA_TranslucentBackground


class ContextMenu(QMenu, QWidget):
    background_color = 'rgba(33, 33, 33, 0.75)'
    hover_color = 'rgba(53, 53, 53, 0.75)'
    button_margins = 10, 6, 0, 6
    checkbox_margins = 10, 11, 0, 8

    def __init__(self, parent: 'Canvas') -> None:
        QMenu.__init__(self, parent)
        QWidget.__init__(self, parent)

        self.parent = parent

        self.setWindowFlag(__windowtype__)
        self.setAttribute(__background__)
        self.setMinimumWidth(80)

        self.menu_items = []
        self.widgets = []

    def _add_item(self,
                  item: ContextMenuItem,
                  binding: Callable = None
                  ) -> None:
        """Wrap the item inside a WidgetAction and add it to the menu."""
        widget = QWidget()
        widget.installEventFilter(self)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        widget.setStyleSheet(str(WidgetStyleSheet(self.background_color)))

        layout = QHBoxLayout(widget)

        if isinstance(item, ContextButton):
            layout.setContentsMargins(*self.button_margins)
        else:
            layout.setContentsMargins(*self.checkbox_margins)

        layout.addWidget(item)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(widget)

        if binding:
            widget_action.triggered.connect(binding)

        self.addAction(widget_action)
        self.menu_items.append(item)
        self.widgets.append(widget)

    def on_mouse_click(self, source: QObject, event: QEvent) -> None:
        source_widget = source.layout().itemAt(0).widget()

        if isinstance(source_widget, ContextButton):
            clicked_widget = source.childAt(event.position().toPoint())

            if (hasattr(clicked_widget, 'name')
                    and clicked_widget.name == 'pin_button'):
                source_widget = source.layout().itemAt(1).widget()

        if Qt.MouseButton.LeftButton & event.button():
            source_widget.on_left_click()
        elif Qt.MouseButton.RightButton & event.button():
            source_widget.on_right_click()

        if isinstance(source_widget, ContextButton):
            self.close()

    def on_mouse_enter(self, source: QObject, event: QEvent) -> None:
        # Prevent triggering outside the widget on Linux
        if event.position().x() < 0 or event.position().y() < 0:
            return

        source_widget = source.layout().itemAt(0).widget()

        for widget, menu_item in zip(self.widgets, self.menu_items):
            widget.setStyleSheet(f'background-color: {self.background_color};')
            menu_item.on_mouse_leave()

        source.setStyleSheet(f'background-color: {self.hover_color};')
        source_widget.on_mouse_enter()

    def on_mouse_leave(self, source: QObject) -> None:
        source_widget = source.layout().itemAt(0).widget()

        source.setStyleSheet(f'background-color: {self.background_color};')
        source_widget.on_mouse_leave()

    def on_key_press(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()

        if event.key() == Qt.Key.Key_A:
            self.parent.parent.prev_image()
            self.close()

        elif event.key() == Qt.Key.Key_D:
            self.parent.parent.next_image()
            self.close()

        elif event.key() == Qt.Key.Key_W:
            self.parent.set_annotating_state(AnnotatingState.READY)
            self.close()

        elif event.key() == Qt.Key.Key_E:
            self.parent.set_annotating_state(AnnotatingState.READY)
            self.parent.quick_create = True
            self.close()

        elif event.text().isdigit():
            self.parent.keyPressEvent(event)
            self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.on_key_press(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        for menu_item in self.menu_items:
            menu_item.on_mouse_leave()

        super().closeEvent(event)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type in (event.Type.MouseButtonPress,
                          event.Type.MouseButtonDblClick):
            self.on_mouse_click(source, event)

        elif event_type == event.Type.HoverMove:
            self.on_mouse_enter(source, event)

        elif event_type == event.Type.HoverLeave:
            self.on_mouse_leave(source)

        return True

    def update(self) -> None:
        for item in self.menu_items:
            item.update()

        super().update()


class CanvasContextMenu(ContextMenu):
    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent)

        self.parent = parent
        self.redraw_widgets()

    def redraw_widgets(self) -> None:
        self.menu_items = []
        self.widgets = []
        self.clear()

        annos = self.parent.annotations
        hidden_annos = [anno for anno in annos if anno.hidden]

        text, should_hide = ('Show All', False) \
            if hidden_annos else ('Hide All', True)

        def set_hidden_all() -> None:
            for anno in self.parent.annotations:
                anno.hidden = should_hide
            self.parent.update()

        def pin_menu() -> None:
            self.parent.parent.annotation_list.setVisible(True)
            self.parent.pin_annotation_list = True

        hide_button = ContextButton(self.parent, set_hidden_all, text, False)
        pin_button = ContextButton(self.parent, pin_menu, ' \u276F ', False)
        pin_button.name = 'pin_button'
        pin_button.setFixedWidth(25)

        buttons_widget = QWidget()
        buttons_widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        buttons_widget.installEventFilter(self)
        buttons_widget.setStyleSheet(
            str(WidgetStyleSheet(self.background_color)))

        layout = QHBoxLayout(buttons_widget)
        layout.setContentsMargins(*self.button_margins)

        layout.addWidget(hide_button)
        layout.addWidget(pin_button)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(buttons_widget)

        self.addAction(widget_action)
        self.addSeparator()

        for annotation in self.parent.annotations[::-1]:
            check_box = ContextCheckBox(self.parent, annotation)
            self._add_item(check_box, None)

    def on_key_press(self, event: QKeyEvent) -> None:
        ctrl_pressed = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift_pressed = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        if ctrl_pressed and event.key() == Qt.Key.Key_C:
            self.parent.copy_annotations()

        elif ctrl_pressed and shift_pressed and event.key() == Qt.Key.Key_V:
            self.parent.paste_annotations(replace_existing=False)
            self.redraw_widgets()

        elif ctrl_pressed and event.key() == Qt.Key.Key_V:
            self.parent.paste_annotations(replace_existing=True)
            self.redraw_widgets()

        elif ctrl_pressed and event.key() == Qt.Key.Key_Z:
            action = self.parent.action_handler.undo()

            if isinstance(action, (ActionCreate, ActionDelete)):
                self.redraw_widgets()
            else:
                self.update()

        elif ctrl_pressed and event.key() == Qt.Key.Key_Y:
            action = self.parent.action_handler.redo()

            if isinstance(action, (ActionCreate, ActionDelete)):
                self.redraw_widgets()
            else:
                self.update()

        elif ctrl_pressed and event.key() == Qt.Key.Key_H:
            self.parent.hide_annotations()
            self.update()

        elif ctrl_pressed and event.key() == Qt.Key.Key_R:
            self.parent.rename_annotations()
            self.update()

        elif ctrl_pressed and event.key() == Qt.Key.Key_A:
            self.parent.select_all()
            self.update()

        elif event.key() == Qt.Key.Key_Space:
            self.parent.select_next_annotation()
            self.update()

        elif event.key() == Qt.Key.Key_Delete:
            self.parent.delete_annotations()
            self.redraw_widgets()

        else:
            super().on_key_press(event)


class AnnotationContextMenu(ContextMenu):
    def __init__(self, parent: 'Canvas', annotation: Annotation) -> None:
        super().__init__(parent)

        def _copy() -> None:
            parent.copy_annotations()
            parent.unselect_all()

        def _rename() -> None:
            parent.rename_annotations()
            parent.unselect_all()

        def _hide() -> None:
            parent.hide_annotations()
            parent.unselect_all()

        def _flip() -> None:
            parent.flip_keypoints()

        def _delete() -> None:
            parent.delete_annotations()
            parent.unselect_all()

        buttons = [
            ContextButton(parent, _copy, 'Copy', False),
            ContextButton(parent, _rename, 'Rename', False),
            ContextButton(parent, _hide, 'Hide', False),
            ContextButton(parent, _delete, 'Delete', True)
        ]

        if annotation.has_keypoints and annotation.label_schema.kpt_symmetry:
            buttons.insert(-1, ContextButton(parent, _flip, 'Flip', False))

        for button in buttons:
            if button.risky:
                self.addSeparator()

            self._add_item(button)
