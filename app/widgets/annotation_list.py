from typing import TYPE_CHECKING, Callable

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, \
    QSpacerItem

from app.styles.style_sheets import WidgetStyleSheet
from app.widgets.context_menu import ContextMenuItem, ContextCheckBox
from app.widgets.menu_item import ContextButton

if TYPE_CHECKING:
    from annotator import MainWindow

__size_policy__ = QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed


class AnnotationList(QWidget):
    background_color = 'rgb(33, 33, 33)'
    hover_color = 'rgb(53, 53, 53)'
    checkbox_margins = 13, 11, 0, 8

    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent

        self.setStyleSheet('border-left: 1px solid rgb(53, 53, 53);')
        self.setFixedWidth(150)
        self.setVisible(False)

        self.menu_items = []
        self.widgets = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.annotations_container = QWidget()
        self.annotations_layout = QVBoxLayout(self.annotations_container)
        self.annotations_layout.setContentsMargins(0, 0, 0, 0)
        self.annotations_layout.setSpacing(10)

        for _ in range(2):
            self.annotations_layout.addItem(
                QSpacerItem(0, 0,
                            QSizePolicy.Policy.Minimum,
                            QSizePolicy.Policy.Expanding))

        self.main_layout.addWidget(self.annotations_container, 1)

        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        self.button_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        def _unpin_menu() -> None:
            self.setVisible(False)
            self.parent.canvas.pin_annotation_list = False

        self.bottom_button = ContextButton(
            parent=self.parent.canvas,
            binding=_unpin_menu,
            text='\u276E',
            risky=False
        )
        self.bottom_button.setSizePolicy(QSizePolicy.Policy.Fixed,
                                         QSizePolicy.Policy.Fixed)

        bottom_wrapper = QWidget()
        bottom_wrapper.installEventFilter(self)
        bottom_wrapper.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        bottom_wrapper.setStyleSheet(
            str(WidgetStyleSheet(self.background_color)))

        bottom_layout = QHBoxLayout(bottom_wrapper)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        bottom_layout.addWidget(self.bottom_button)

        self.button_layout.addWidget(bottom_wrapper)
        self.main_layout.addLayout(self.button_layout)

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

        widget.setSizePolicy(*__size_policy__)
        item.setSizePolicy(*__size_policy__)

        if binding:
            item.clicked.connect(binding)

        # Insert the unpin button before the bottom spacer (last item)
        insert_position = self.annotations_layout.count() - 1
        self.annotations_layout.insertWidget(insert_position, widget)

        self.menu_items.append(item)
        self.widgets.append(widget)

    def redraw_widgets(self) -> None:
        # Remove old items excluding spacers (first and last items)
        while self.annotations_layout.count() > 2:
            child = self.annotations_layout.itemAt(1)

            if child and child.widget():
                w = child.widget()

                self.annotations_layout.removeWidget(w)
                w.deleteLater()

        self.menu_items = []
        self.widgets = []

        annotations = self.parent.canvas.annotations[::-1]
        annotations = sorted(annotations, key=lambda a: a.category_id)

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
