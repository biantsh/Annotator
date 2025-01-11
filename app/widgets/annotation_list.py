from typing import TYPE_CHECKING, Callable

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem
)

from app.objects import Annotation, Keypoint
from app.styles.style_sheets import WidgetStyleSheet, ListCheckBoxStyleSheet
from app.widgets.context_menu import ContextCheckBox
from app.widgets.menu_item import ContextButton
from app.utils import pretty_text, text_to_color

if TYPE_CHECKING:
    from annotator import MainWindow

__size_policy__ = QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding


class ListItemCheckBox(ContextCheckBox):
    def __init__(self, *args, **kwargs) -> None:
        self.hovered = False
        super().__init__(*args, **kwargs)

    def update(self) -> None:
        selected = self.annotation.selected
        checkbox_color = text_to_color(self.annotation.label_name)

        label = pretty_text(self.annotation.label_name)
        padded_length = len(label) + 30

        self.setStyleSheet(str(ListCheckBoxStyleSheet(selected, self.hovered, checkbox_color)))
        self.setChecked(not self.annotation.hidden)
        self.setText(label.ljust(padded_length))


class ListItemArrow(QLabel):
    def __init__(self) -> None:
        super().__init__('\u276F')
        self.setStyleSheet('border-left: None;')
        self.setContentsMargins(0, 0, 0, 6)

    def set_expanded(self, expanded: bool) -> None:
        self.setText('\u276E' if expanded else '\u276F')


class KeypointItem(QWidget):
    def __init__(self, parent: 'KeypointList', keypoint: Keypoint) -> None:
        super().__init__()

        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Fixed))

        self.parent = parent

        self.annotation = keypoint.parent
        self.index = keypoint.index

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        annotation = keypoint.parent
        keypoint_name = annotation.kpt_names[keypoint.index]

        self.keypoint_label = QLabel(pretty_text(keypoint_name))
        self.keypoint_label.setContentsMargins(16, 0, 0, 0)
        self.keypoint_label.setStyleSheet('''
            border-left: None;
            font-weight: bold;
            font-size: 9pt;
            min-height: 25px;
            max-height: 25px;
        ''')

        layout.addWidget(self.keypoint_label)

        self.hovered = False

    @property
    def keypoint(self) -> Keypoint:
        return self.annotation.keypoints[self.index]

    def set_hovered(self, hovered: bool) -> None:
        self.hovered = hovered
        self.update()

    def update(self) -> None:
        color = (200, 200, 200) if self.keypoint.visible else (82, 82, 82)
        background = (53, 53, 53) if self.keypoint.selected or self.hovered \
            else (33, 33, 33)

        self.keypoint_label.setStyleSheet(f'''
            background-color: rgb{background};
            color: rgb{color};
            border-left: None;
            font-weight: bold;
            font-size: 9pt;
            min-height: 25px;
            max-height: 25px;
        ''')


class KeypointList(QWidget):
    def __init__(self, parent: 'ListItem', annotation: Annotation) -> None:
        super().__init__()

        self.parent = parent
        self.annotation = annotation

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.keypoint_items = []

        for keypoint in annotation.keypoints:
            item = KeypointItem(self, keypoint)
            item.installEventFilter(self)
            layout.addWidget(item)

            self.keypoint_items.append(item)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type in (event.Type.MouseButtonPress,
                          event.Type.MouseButtonDblClick):
            if not source.keypoint.visible:
                return True

            if Qt.MouseButton.LeftButton & event.button():
                canvas = self.parent.canvas
                keypoint = source.keypoint

                if Qt.KeyboardModifier.ControlModifier & event.modifiers():
                    if keypoint in canvas.selected_keypoints:
                        canvas.unselect_keypoint(keypoint)

                    else:
                        canvas.add_selected_keypoint(keypoint)

                else:
                    canvas.set_selected_keypoint(keypoint)

                canvas.update()

        elif event_type == event.Type.Enter:
            source.set_hovered(True)

        elif event_type == event.Type.Leave:
            source.set_hovered(False)

        else:
            return False

        return True

    def update(self) -> None:
        for item in self.keypoint_items:
            item.update()


class ListItem(QWidget):
    def __init__(self,
                 parent: 'AnnotationList',
                 annotation: Annotation
                 ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.canvas = parent.parent.canvas

        self.annotation = annotation

        self.header = QWidget(self)
        self.header.setContentsMargins(8, 0, 0, 0)
        self.header.installEventFilter(self)

        self.checkbox = ListItemCheckBox(self.canvas, self.annotation)
        self.checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.arrow = ListItemArrow()

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.keypoints_drawn = False
        self.keypoint_widget = KeypointList(self, annotation)

        self.horizontal_layout = QHBoxLayout()
        self.horizontal_layout.setContentsMargins(0, 13, 5, 6)

        self.horizontal_layout.addWidget(self.checkbox)

        self.header.setLayout(self.horizontal_layout)
        self.header.setStyleSheet('border: none;')

        self.layout.addWidget(self.header)
        self.setLayout(self.layout)

        self.update()

    def update(self) -> None:
        if self.annotation.has_keypoints:
            if self.horizontal_layout.count() == 1:
                self.horizontal_layout.addWidget(self.arrow)
                self.arrow.show()

        elif self.horizontal_layout.count() == 2:
            self.horizontal_layout.removeWidget(self.arrow)
            self.arrow.hide()

        self.checkbox.update()

        selected = (self.canvas.selected_annos
                    and self.canvas.selected_annos[-1] == self.annotation) \
                    or \
                   (self.canvas.selected_keypoints
                    and self.canvas.selected_keypoints[-1].parent == self.annotation)
        has_keypoints = self.annotation.has_keypoints

        if selected and has_keypoints:
            if not self.keypoints_drawn:
                self.layout.addWidget(self.keypoint_widget)
                self.keypoints_drawn = True
                self.arrow.set_expanded(True)

        else:
            if self.keypoints_drawn:
                self.layout.removeWidget(self.keypoint_widget)
                self.keypoints_drawn = False
                self.arrow.set_expanded(False)

        self.keypoint_widget.update()

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type in (event.Type.MouseButtonPress,
                          event.Type.MouseButtonDblClick):
            if Qt.MouseButton.LeftButton & event.button():
                self.checkbox.on_left_click()

            elif Qt.MouseButton.RightButton & event.button():
                self.checkbox.on_right_click()

        elif event_type == event.Type.Enter:
            self.checkbox.hovered = True
            self.checkbox.update()
            source.setStyleSheet('''
                background-color: rgb(53, 53, 53);
                border: none;
            ''')

        elif event_type == event.Type.Leave:
            self.checkbox.hovered = False
            self.checkbox.update()
            source.setStyleSheet('''
                background-color: rgb(33, 33, 33);
                border: none;
            ''')

        else:
            return False

        return True


class AnnotationList(QWidget):
    background_color = 'rgb(33, 33, 33)'
    hover_color = 'rgb(53, 53, 53)'
    checkbox_margins = 0, 0, 0, 8

    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent

        self.menu_items = []
        self.widgets = []

        self.setVisible(True)
        self.setFixedWidth(150)
        self.setStyleSheet('border-left: 1px solid rgb(53, 53, 53);')

        self.anno_container = QWidget()
        self.anno_layout = QVBoxLayout(self.anno_container)
        self.anno_layout.setContentsMargins(0, 0, 0, 0)
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
                  item: ListItem,
                  binding: Callable = None
                  ) -> None:
        widget = QWidget()
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
        annotations = sorted(annotations, key=lambda anno: anno.label_name)

        for annotation in annotations:
            self._add_item(ListItem(self.parent.canvas, annotation), None)

    def on_mouse_click(self, source: QObject, event: QEvent) -> None:
        source_widget = source.layout().itemAt(0).widget() \
            if source.layout() else source

        if Qt.MouseButton.LeftButton & event.button() \
                and hasattr(source_widget, 'on_left_click'):
            source_widget.on_left_click()

        elif Qt.MouseButton.RightButton & event.button() \
                and hasattr(source_widget, 'on_right_click'):
            source_widget.on_right_click()

    def on_mouse_enter(self, source: QObject, event: QEvent) -> None:
        # Prevent triggering outside the widget on Linux
        if event.position().x() < 0 or event.position().y() < 0:
            return

        source_widget = source.layout().itemAt(0).widget() \
            if source.layout() else source

        if hasattr(source_widget, 'on_mouse_enter'):
            source.setStyleSheet(f'background-color: {self.hover_color};')
            source_widget.on_mouse_enter()

    def on_mouse_leave(self, source: QObject) -> None:
        source_widget = source.layout().itemAt(0).widget() \
            if source.layout() else source

        if hasattr(source_widget, 'on_mouse_leave'):
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
