from typing import TYPE_CHECKING, Callable

import rapidfuzz
from rapidfuzz.fuzz import partial_ratio
from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QWidget,
    QWidgetAction,
    QHBoxLayout,
    QMenu,
    QLabel,
    QLineEdit
)

from app.utils import clip_value, pretty_text, text_to_color

if TYPE_CHECKING:
    from app.canvas import Canvas

__windowtype__ = Qt.WindowType.FramelessWindowHint
__background__ = Qt.WidgetAttribute.WA_TranslucentBackground


class ComboBox(QMenu, QWidget):
    def __init__(self,
                 parent: 'Canvas',
                 options: list[str],
                 placeholder_text: str,
                 get_num_labels: Callable
                 ) -> None:
        QMenu.__init__(self, parent)
        QWidget.__init__(self, parent)

        self.parent = parent
        self.widgets = []

        self.setWindowFlag(__windowtype__)
        self.setAttribute(__background__)

        self.selected_index = 0
        self.selected_value = None

        self.options = options
        self.num_results = get_num_labels()

        self.labels_filtered = options[:self.num_results]
        self.label_widgets = [QLabel() for _ in range(self.num_results)]

        self.text_widget = QLineEdit()
        self.text_widget.setAttribute(__background__)
        self.text_widget.setPlaceholderText(placeholder_text)
        self.text_widget.returnPressed.connect(self._select)
        self.text_widget.textChanged.connect(self._on_text_changed)

        self._add_item(self.text_widget)
        self.addSeparator()

        for widget in self.label_widgets:
            self._add_item(widget)
            self.widgets.append(widget)

        self.update()

    def _add_item(self, item: QWidget) -> None:
        widget = QWidget()
        widget.installEventFilter(self)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        layout = QHBoxLayout(widget)
        layout.addWidget(item)

        margins = [4, 6] * 2 if isinstance(item, QLineEdit) else [4, 8] * 2
        layout.setContentsMargins(*margins)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(widget)

        self.addAction(widget_action)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            self._on_key_press(event)

        if not source.layout():
            return True

        source_widget = source.layout().itemAt(0).widget()

        if event.type() == event.Type.HoverMove:
            self._on_mouse_hover(source_widget)

        elif event.type() == event.Type.MouseButtonPress:
            self._select()

        return True

    def showEvent(self, event) -> None:
        super().showEvent(event)

        self.text_widget.setFocus()
        self.parent.update_cursor_icon(Qt.CursorShape.ArrowCursor)

    def _on_text_changed(self) -> None:
        pass

    def _on_key_press(self, event: QKeyEvent) -> None:
        pass

    def _on_mouse_hover(self, widget: QWidget) -> None:
        pass

    def _select(self) -> None:
        pass


class AnnotationComboBox(ComboBox):
    def __init__(self, parent: 'Canvas', labels: list[str]) -> None:
        def get_num_labels() -> int:
            return clip_value(len(labels), 1, 5)

        super().__init__(parent, labels, 'Category', get_num_labels)

    def _sort_labels(self, target: str) -> list[str]:
        target = target.lower().replace(' ', '_')

        matches = rapidfuzz.process.extract(target,
                                            self.options,
                                            scorer=partial_ratio,
                                            limit=self.num_results)

        return [match[0] for match in matches]

    def _on_text_changed(self) -> None:
        target = self.text_widget.text()
        self.labels_filtered = self._sort_labels(target)

        self.update()

    def _on_key_press(self, event: QKeyEvent) -> None:
        index = self.selected_index

        if event.key() == Qt.Key.Key_Up:
            index -= 1
        elif event.key() == Qt.Key.Key_Down:
            index += 1
        elif event.key() == Qt.Key.Key_Escape:
            self.close()

        self.selected_index = clip_value(index, 0, self.num_results - 1)
        self.update()

    def _on_mouse_hover(self, widget: QWidget) -> None:
        if not isinstance(widget, QLabel):
            return

        self.selected_index = self.label_widgets.index(widget)
        self.update()

    def _select(self) -> None:
        if not self.labels_filtered:
            return

        self.selected_value = self.labels_filtered[self.selected_index]
        self.close()

    def update(self) -> None:
        if not self.labels_filtered:
            self.label_widgets[0].setText('<i>No labels available</i>')
            return

        selected_text = self.labels_filtered[self.selected_index]
        underline_color = text_to_color(selected_text)

        for widget, label in zip(self.label_widgets, self.labels_filtered):
            widget.setStyleSheet('border: none; border-bottom: none;')
            widget.setText(pretty_text(label))

        self.label_widgets[self.selected_index].setStyleSheet(
            f'border: none; border-bottom: 2px solid rgb{underline_color};')


class ImageComboBox(ComboBox):
    def __init__(self, parent: 'Canvas', image_names: list[str]) -> None:
        super().__init__(parent, image_names, 'Find image by name', lambda: 5)

        self._set_width()
        self._on_text_changed()

        self.update()

    def _set_width(self) -> None:
        label_widget = self.label_widgets[0]
        text_length = label_widget.fontMetrics().horizontalAdvance

        label_widget.setText(max(self.options, key=text_length))
        label_widget.adjustSize()

        label_widget.setFixedWidth(self.label_widgets[0].width() + 75)

    def _on_text_changed(self) -> None:
        search = self.text_widget.text()
        filtered_names = [name for name in self.options if search in name]

        for widget in self.widgets:
            widget.setText('')

        for index, name in enumerate(filtered_names[:self.num_results]):
            self.widgets[index].setText(name)

        self.selected_index = 0
        self.update()

    def _on_key_press(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            index = (-1 if event.key() == Qt.Key.Key_Up else 1) \
                + self.selected_index

            if 0 <= index < len(self.widgets) and self.widgets[index].text():
                self.selected_index = index

        elif event.key() == Qt.Key.Key_Escape:
            self.close()

        self.update()

    def _on_mouse_hover(self, widget: QWidget) -> None:
        if not (isinstance(widget, QLabel) and widget.text()):
            return

        self.selected_index = self.widgets.index(widget)
        self.update()

    def _select(self) -> None:
        self.selected_value = self.widgets[self.selected_index].text()
        self.close()

    def update(self) -> None:
        for index, widget in enumerate(self.widgets):
            color = (255, 255, 255) if index == self.selected_index \
                else (200, 200, 200)

            widget.setStyleSheet(f'color: rgb{color};')
