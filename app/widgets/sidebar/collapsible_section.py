import os
import sys

from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QMouseEvent, QCursor, QPixmap, QColor
from PyQt6.QtWidgets import (
    QGraphicsColorizeEffect,
    QApplication,
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel
)

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')

__smooth_transform__ = Qt.TransformationMode.SmoothTransformation


class CollapsibleSection(QWidget):
    def __init__(self, title: str, collapsed: bool) -> None:
        super().__init__()

        self.header = CollapsibleSectionHeader(self, title)
        self.content_area = QWidget(self)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.header)
        main_layout.addWidget(self.content_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self._is_collapsed = False
        self.collapse() if collapsed else self.expand()

    def set_count(self, count: int) -> None:
        self.header.count_label.setText(str(count))

    def toggle(self) -> None:
        self.expand() if self._is_collapsed else self.collapse()

    def collapse(self) -> None:
        self._is_collapsed = True
        self.content_area.hide()

        arrow = QPixmap(os.path.join(__iconpath__, 'arrow_right.png'))
        self.header.arrow_label.setPixmap(arrow.scaled(10, 10))

    def expand(self) -> None:
        self._is_collapsed = False
        self.content_area.show()

        arrow = QPixmap(os.path.join(__iconpath__, 'arrow_down.png'))
        self.header.arrow_label.setPixmap(arrow.scaled(10, 10))


class CollapsibleSectionHeader(QWidget):
    def __init__(self, parent: CollapsibleSection, title: str) -> None:
        super().__init__(parent)
        self.parent = parent

        self.count_label = CollapsibleSectionCount()
        self.title_label = CollapsibleSectionTitle(title)
        self.arrow_label = CollapsibleSectionArrow()

        layout = QHBoxLayout(self)
        layout.addWidget(self.count_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.arrow_label)

        layout.setContentsMargins(4, 6, 2, 6)
        layout.setSpacing(0)

    def highlight(self) -> None:
        effect = QGraphicsColorizeEffect(self.arrow_label)
        effect.setColor(QColor(223, 223, 223))

        self.setStyleSheet('color: rgb(223, 223, 223);')
        self.arrow_label.setGraphicsEffect(effect)

    def unhighlight(self) -> None:
        self.setStyleSheet('color: rgb(153, 153, 153);')
        self.arrow_label.setGraphicsEffect(None)

    def enterEvent(self, event: QEvent) -> None:
        self.highlight()

    def leaveEvent(self, event: QEvent) -> None:
        self.unhighlight()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.parent.toggle()
        QTimer.singleShot(0, self._on_click)

    def _on_click(self) -> None:
        QApplication.processEvents()
        mouse_pos = self.mapFromGlobal(QCursor.pos())

        if not self.rect().contains(mouse_pos):
            self.unhighlight()


class CollapsibleSectionCount(QLabel):
    def __init__(self) -> None:
        super().__init__()

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class CollapsibleSectionTitle(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__(title)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)


class CollapsibleSectionArrow(QLabel):
    def __init__(self) -> None:
        super().__init__()

        self.setSizePolicy(QSizePolicy.Policy.Fixed,
                           QSizePolicy.Policy.Fixed)
