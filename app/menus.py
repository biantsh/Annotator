from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtWidgets import QMenu, QWidgetAction, QLabel, QWidget, QHBoxLayout

if TYPE_CHECKING:
    from app.canvas import Canvas


class AnnotationContextMenu(QMenu):
    background_color = '#2a2b2f'
    hover_color = '#46464a'
    margins = 10, 3, 0, 3
    min_width = 70

    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent)

        self.add_action('Rename', parent.rename_annotation, False)
        self.add_action('Hide', parent.hide_annotation, False)

        self.addSeparator()

        self.add_action('Delete', parent.delete_annotation, True)

    def add_action(self,
                   label_text: str,
                   binding: Callable,
                   risky: bool
                   ) -> None:
        widget_action = QWidgetAction(self)

        widget = QWidget()
        widget.installEventFilter(self)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(*self.margins)

        label = QLabel(label_text)
        layout.addWidget(label)

        widget.setStyleSheet(f"""
            background-color: {self.background_color};
            min-width: {self.min_width};
        """)
        label.setStyleSheet(f"""
            color: {'red' if risky else 'white'};
            font-weight: {'bold' if risky else 'normal'};
        """)

        widget_action.setDefaultWidget(widget)
        widget_action.triggered.connect(binding)

        self.addAction(widget_action)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type in (QEvent.Type.HoverEnter, QEvent.Type.HoverMove):
            obj.setStyleSheet(f'background-color: {self.hover_color};')
        elif event_type == QEvent.Type.HoverLeave:
            obj.setStyleSheet(f'background-color: {self.background_color};')

        return super().eventFilter(obj, event)
