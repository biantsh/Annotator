from typing import Callable

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QEnterEvent, QMouseEvent
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QLabel


class ClickableLabel(QLabel):
    def __init__(self, text: str, binding: Callable) -> None:
        super().__init__(text)

        self.binding = binding
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _set_underline(self, underline: bool) -> None:
        font = self.font()

        font.setUnderline(underline)
        self.setFont(font)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._set_underline(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._set_underline(False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.binding()

        super().mouseReleaseEvent(event)


class InteractiveLabel(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(self.fontMetrics().horizontalAdvance(' '))

    def add_text(self, text: str) -> None:
        self.layout.addWidget(QLabel(text))

    def add_hypertext(self, text: str, binding: Callable) -> None:
        self.layout.addWidget(ClickableLabel(text, binding))

    def clear(self) -> None:
        for _ in range(self.layout.count()):
            self.layout.takeAt(0).widget().deleteLater()
