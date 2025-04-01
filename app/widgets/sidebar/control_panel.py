import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QEvent, QObject, QTimer, QPoint
from PyQt6.QtGui import QMouseEvent, QPixmap
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QWidget, QLabel

if TYPE_CHECKING:
    from app.widgets.sidebar.annotation_list import AnnotationList

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')

__smooth_transform__ = Qt.TransformationMode.SmoothTransformation


class ControlPanel(QWidget):
    def __init__(self, parent: 'AnnotationList') -> None:
        super().__init__()
        self.parent = parent

        self.unpin_button = UnpinButton(parent)
        self.unpin_button.installEventFilter(self)

        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.copy_image_button = CopyImageButton(parent)
        self.copy_image_button.installEventFilter(self)
        self.copy_image_button.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.unpin_button)
        layout.addStretch()
        layout.addWidget(self.progress_label)
        layout.addStretch()
        layout.addWidget(self.copy_image_button)

    def redraw(self) -> None:
        main_window = self.parent.parent
        image_name = main_window.canvas.image_name

        current_image = main_window.image_controller.index
        num_images = main_window.image_controller.num_images

        self.progress_label.setText(f'{current_image + 1} / {num_images}')
        self.copy_image_button.tooltip.setText(image_name)
        self.copy_image_button.tooltip.adjustSize()

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() == event.Type.Enter:
            source.setStyleSheet('background-color: rgb(53, 53, 53);')

        elif event.type() == event.Type.Leave:
            source.setStyleSheet('background-color: transparent;')

        return False


class UnpinButton(QLabel):
    def __init__(self, parent: 'AnnotationList') -> None:
        super().__init__('\u276E')
        self.parent = parent

    def mousePressEvent(self, _: QMouseEvent) -> None:
        self.parent.setVisible(not self.parent.isVisible())


class CopyImageButton(QLabel):
    def __init__(self, parent: 'AnnotationList') -> None:
        super().__init__(parent)

        self.parent = parent
        self.setFixedSize(28, 32)

        self.copy_icon = QPixmap(os.path.join(__iconpath__, 'copy.svg')) \
            .scaled(17, 17)
        self.check_icon = QPixmap(os.path.join(__iconpath__, 'check.png')) \
            .scaled(16, 16, transformMode=__smooth_transform__)

        self.setPixmap(self.copy_icon)
        self.tooltip = ImageTooltip(parent)

        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setInterval(550)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_tooltip)

        self.icon_timer = QTimer(self)
        self.icon_timer.setInterval(2500)
        self.icon_timer.setSingleShot(True)
        self.icon_timer.timeout.connect(
            lambda: self.setPixmap(self.copy_icon))

    def show_tooltip(self) -> None:
        window = self.parent.parent

        button_position = self.mapToGlobal(self.rect().topLeft())
        width, height = self.tooltip.width(), self.tooltip.height()

        top_bar = window.geometry().top() - window.frameGeometry().top()
        offset = window.pos() + QPoint(width - 10, top_bar + height - 10)

        self.tooltip.move(button_position - offset)
        self.tooltip.raise_()
        self.tooltip.show()

    def enterEvent(self, event: QMouseEvent) -> None:
        self.tooltip_timer.start()

    def leaveEvent(self, event: QMouseEvent) -> None:
        self.tooltip_timer.stop()
        self.tooltip.hide()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.parent.parent.canvas.image_name)

        self.setPixmap(self.check_icon)
        self.icon_timer.start()

        self.tooltip.hide()


class ImageTooltip(QLabel):
    def __init__(self, parent: 'AnnotationList') -> None:
        super().__init__(parent.parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
