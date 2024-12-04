from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtWidgets import (
    QMenu,
    QHBoxLayout,
    QWidgetAction,
    QWidget
)

from app.styles.style_sheets import WidgetStyleSheet
from app.widgets.menu_item import (
    ContextMenuItem,
    ContextButton,
    ContextCheckBox
)

if TYPE_CHECKING:
    from app.canvas import Canvas

__background__ = Qt.WidgetAttribute.WA_TranslucentBackground


class ContextMenu(QMenu):
    background_color = 'rgba(33, 33, 33, 0.75)'
    hover_color = 'rgba(53, 53, 53, 0.75)'
    button_margins = 10, 6, 0, 6
    checkbox_margins = 10, 11, 0, 11

    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent)
        self.setAttribute(__background__)

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

    def on_mouse_click(self, source: QObject) -> None:
        source_widget = source.layout().itemAt(0).widget()
        source_widget.on_mouse_click()

        if isinstance(source_widget, ContextButton):
            self.close()

    def on_mouse_enter(self, source: QObject) -> None:
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

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type in (event.Type.MouseButtonPress,
                          event.Type.MouseButtonDblClick):
            self.on_mouse_click(source)

        elif event_type == event.Type.Enter:
            self.on_mouse_enter(source)

        elif event_type == event.Type.Leave:
            self.on_mouse_leave(source)

        return True


class CanvasContextMenu(ContextMenu):
    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent)

        hidden_annos = parent.get_hidden_annotations()
        text, should_hide = ('Show All', False) \
            if hidden_annos else ('Hide All', True)

        def set_hidden_all() -> None:
            for anno in parent.annotations:
                anno.hidden = should_hide

            parent.update()

        self._add_item(ContextButton(parent, set_hidden_all, text, False))
        self.addSeparator()

        for annotation in parent.annotations[::-1]:  # Prioritize newer annos
            self._add_item(ContextCheckBox(parent, annotation), None)


class AnnotationContextMenu(ContextMenu):
    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent)

        buttons = (
            ContextButton(parent, parent.copy_annotations, 'Copy', False),
            ContextButton(parent, parent.rename_annotations, 'Rename', False),
            ContextButton(parent, parent.hide_annotations, 'Hide', False),
            ContextButton(parent, parent.delete_annotations, 'Delete', True)
        )

        for button in buttons:
            if button.risky:
                self.addSeparator()

            self._add_item(button)
