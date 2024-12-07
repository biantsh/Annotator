from typing import TYPE_CHECKING

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
    def __init__(self, parent: 'Canvas', labels: list[str]) -> None:
        QMenu.__init__(self, parent)
        QWidget.__init__(self)
        self.parent = parent

        self.setWindowFlag(__windowtype__)
        self.setAttribute(__background__)

        self.selected_index = 0
        self.selected_value = None

        self.labels = labels
        self.num_labels = min(len(labels), 5)

        self.labels_filtered = labels[:self.num_labels]
        self.label_widgets = [QLabel() for _ in range(self.num_labels)]

        self.text_widget = QLineEdit()
        self.text_widget.setAttribute(__background__)
        self.text_widget.setPlaceholderText('Category')
        self.text_widget.returnPressed.connect(self._select)
        self.text_widget.textChanged.connect(self._on_text_changed)

        self._add_item(self.text_widget)
        self.addSeparator()

        for widget in self.label_widgets:
            self._add_item(widget)

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

    def _sort_labels(self, target: str) -> list[str]:
        target = target.lower().replace(' ', '_')
        labels = self.labels

        matches = rapidfuzz.process.extract(target,
                                            labels,
                                            scorer=partial_ratio,
                                            limit=self.num_labels)

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

        self.selected_index = clip_value(index, 0, self.num_labels - 1)
        self.update()

    def _on_mouse_hover(self, widget: QWidget) -> None:
        if not isinstance(widget, QLabel):
            return

        self.selected_index = self.label_widgets.index(widget)
        self.update()

    def _select(self) -> None:
        self.selected_value = self.labels_filtered[self.selected_index]
        self.close()

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type == QEvent.Type.KeyPress:
            self._on_key_press(event)

        if not source.layout():
            return True

        source_widget = source.layout().itemAt(0).widget()

        if event_type == event.Type.HoverMove:
            self._on_mouse_hover(source_widget)

        elif event_type == event.Type.MouseButtonPress:
            self._select()

        return True

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.text_widget.setFocus()

    def update(self) -> None:
        selected_text = self.labels_filtered[self.selected_index]
        underline_color = text_to_color(selected_text)

        for widget, label in zip(self.label_widgets, self.labels_filtered):
            widget.setText(pretty_text(label))

            widget.setStyleSheet('border: none; border-bottom: none;')

        self.label_widgets[self.selected_index].setStyleSheet(
            f'border: none; border-bottom: 2px solid rgb{underline_color};')

        super().update()
