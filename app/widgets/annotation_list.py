from typing import TYPE_CHECKING, Callable

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, \
    QSpacerItem

from app.styles.style_sheets import WidgetStyleSheet
from app.widgets.context_menu import ContextMenuItem, ContextCheckBox
from app.widgets.menu_item import ContextButton

if TYPE_CHECKING:
    from annotator import MainWindow

__size_policy__ = QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding


class AnnotationList(QWidget):
    background_color = 'rgb(33, 33, 33)'
    hover_color = 'rgb(53, 53, 53)'
    checkbox_margins = 13, 11, 0, 8

    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent

        self.menu_items = []
        self.widgets = []

        self.setVisible(False)
        self.setFixedWidth(150)
        self.setStyleSheet('border-left: 1px solid rgb(53, 53, 53);')

        self.anno_container = QWidget()
        self.anno_layout = QVBoxLayout(self.anno_container)
        self.anno_layout.setContentsMargins(0, 0, 0, 0)
        self.anno_layout.setSpacing(10)

        for _ in range(2):
            self.anno_layout.addItem(QSpacerItem(0, 0, *__size_policy__))

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.anno_container)

        def _unpin() -> None:
            self.setVisible(False)
            self.parent.canvas.pin_annotation_list = False

        self.unpin_button = ContextButton(
            parent=self.parent.canvas,
            binding=_unpin,
            text='\u276E',
            risky=False
        )

        unpin_wrapper = QWidget()
        unpin_wrapper.installEventFilter(self)
        unpin_wrapper.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        unpin_layout = QHBoxLayout(unpin_wrapper)
        unpin_layout.addWidget(self.unpin_button)

        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addWidget(unpin_wrapper)
        self.main_layout.addLayout(self.bottom_layout)

    def _add_item(self,
                  item: ContextMenuItem,
                  binding: Callable = None
                  ) -> None:
        widget = QWidget()
        widget.installEventFilter(self)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        widget.setStyleSheet(str(WidgetStyleSheet(self.background_color)))

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(*self.checkbox_margins)
        layout.addWidget(item)

        if binding:
            item.clicked.connect(binding)

        # Insert the unpin button before the bottom spacer (last item)
        insert_position = self.anno_layout.count() - 1
        self.anno_layout.insertWidget(insert_position, widget)

        self.menu_items.append(item)
        self.widgets.append(widget)

    def redraw_widgets(self) -> None:
        # Remove old items excluding spacers (first and last items)
        while self.anno_layout.count() > 2:
            widget = self.anno_layout.itemAt(1).widget()
            self.anno_layout.removeWidget(widget)

        self.menu_items = []
        self.widgets = []

        annotations = self.parent.canvas.annotations[::-1]
        annotations = sorted(annotations, key=lambda anno: anno.category_id)

        for annotation in annotations:
            check_box = ContextCheckBox(self.parent.canvas, annotation)
            self._add_item(check_box, None)

    def on_mouse_click(self, source: QObject, event: QEvent) -> None:
        source_widget = source.layout().itemAt(0).widget() \
            if source.layout() else source

        if Qt.MouseButton.LeftButton & event.button():
            source_widget.on_left_click()
        elif Qt.MouseButton.RightButton & event.button():
            source_widget.on_right_click()

    def on_mouse_enter(self, source: QObject, event: QEvent) -> None:
        # Prevent triggering outside the widget on Linux
        if event.position().x() < 0 or event.position().y() < 0:
            return

        source_widget = source.layout().itemAt(0).widget() \
            if source.layout() else source

        for widget, menu_item in zip(self.widgets, self.menu_items):
            widget.setStyleSheet(f'background-color: {self.background_color};')
            menu_item.on_mouse_leave()

        source.setStyleSheet(f'background-color: {self.hover_color};')
        source_widget.on_mouse_enter()

    def on_mouse_leave(self, source: QObject) -> None:
        source_widget = source.layout().itemAt(0).widget() \
            if source.layout() else source

        source.setStyleSheet(f'background-color: {self.background_color};')

        if hasattr(source_widget, 'on_mouse_leave'):
            source_widget.on_mouse_leave()

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type in (event.Type.MouseButtonPress,
                          event.Type.MouseButtonDblClick):
            self.on_mouse_click(source, event)

        elif event_type == event.Type.HoverMove:
            self.on_mouse_enter(source, event)

        elif event_type == event.Type.HoverLeave:
            self.on_mouse_leave(source)

        else:
            return False

        return True

    def update(self) -> None:
        for widget in self.menu_items:
            widget.update()

        super().update()
