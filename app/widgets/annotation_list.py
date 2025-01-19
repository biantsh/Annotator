import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent, QPoint, QTimer
from PyQt6.QtGui import QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel
)

from app.enums.canvas import AnnotatingState
from app.objects import Annotation, Keypoint
from app.utils import pretty_text
from app.widgets.context_menu import ContextCheckBox

if TYPE_CHECKING:
    from annotator import MainWindow
    from app.canvas import Canvas

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')

__smooth_transform__ = Qt.TransformationMode.SmoothTransformation


class AnnotationList(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent

        main_layout = QVBoxLayout(self)
        self.anno_layout = QVBoxLayout()
        self.control_panel = ControlPanel(self)

        main_layout.addStretch()
        main_layout.addLayout(self.anno_layout)
        main_layout.addStretch()
        main_layout.addWidget(self.control_panel)

        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def redraw_widgets(self) -> None:
        annos = self.parent.canvas.annotations.copy()
        annotator = self.parent.canvas.keypoint_annotator

        if annotator.active and annotator.annotation not in annos:
            annos.append(annotator.annotation)

        for index in range(self.anno_layout.count()):
            self.anno_layout.itemAt(index).widget().deleteLater()

        for anno in sorted(annos, key=lambda anno: anno.label_name):
            self.anno_layout.addWidget(ListItem(self.parent.canvas, anno))

        self.control_panel.redraw()

    def update(self) -> None:
        for index in range(self.anno_layout.count()):
            self.anno_layout.itemAt(index).widget().update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.parent.canvas.keypoint_annotator.active:
            self.parent.canvas.keypoint_annotator.end()


class ListItem(QWidget):
    def __init__(self, canvas: 'Canvas', annotation: Annotation) -> None:
        super().__init__()

        self.canvas = canvas
        self.annotation = annotation

        self.checkbox = ContextCheckBox(self.canvas, self.annotation)
        self.keypoint_list = KeypointList(self, annotation)
        self.arrow = QLabel()

        header = QWidget(self)
        header.installEventFilter(self)

        self.layout = QVBoxLayout()
        self.layout.addWidget(header)
        self.layout.addWidget(self.keypoint_list)

        self.header_layout = QHBoxLayout()
        self.header_layout.addWidget(self.checkbox)
        self.header_layout.addWidget(self.arrow)

        header.setLayout(self.header_layout)
        self.setLayout(self.layout)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setContentsMargins(8, 9, 1, 6)

        self.update()

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() in (event.Type.MouseButtonPress,
                            event.Type.MouseButtonDblClick):
            if self.canvas.keypoint_annotator.active:
                self.canvas.keypoint_annotator.end()
                self.checkbox.on_mouse_leave()

            if Qt.MouseButton.LeftButton & event.button():
                self.checkbox.on_left_click()

            elif Qt.MouseButton.RightButton & event.button():
                self.checkbox.on_right_click()

        elif event.type() == event.Type.Enter:
            source.setStyleSheet('background-color: rgb(53, 53, 53);')
            self.checkbox.on_mouse_enter()

        elif event.type() == event.Type.Leave:
            source.setStyleSheet('background-color: rgb(33, 33, 33);')
            self.checkbox.on_mouse_leave()

        return False

    def update(self) -> None:
        anno = self.annotation
        selected_annos = self.canvas.selected_annos
        selected_kpts = self.canvas.selected_keypoints

        self.arrow.show() if anno.kpt_names else self.arrow.hide()
        self.keypoint_list.update()
        self.checkbox.update()

        if selected_kpts and all(kpt.parent == anno for kpt in selected_kpts) \
                or selected_annos == [anno]:
            self.keypoint_list.show()
            self.arrow.setText('\u276E')

        else:
            self.keypoint_list.hide()
            self.arrow.setText('\u276F')


class KeypointList(QWidget):
    def __init__(self, parent: ListItem, annotation: Annotation) -> None:
        super().__init__()

        self.parent = parent
        self.annotation = annotation

        layout = QVBoxLayout()
        self.setLayout(layout)

        for keypoint in annotation.keypoints:
            layout.addWidget(KeypointItem(self.parent, keypoint))

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def update(self) -> None:
        for index in range(self.layout().count()):
            self.layout().itemAt(index).widget().update()


class KeypointItem(QWidget):
    def __init__(self, parent: ListItem, keypoint: Keypoint) -> None:
        super().__init__()

        self.parent = parent
        self.keypoint = keypoint

        keypoint_name = keypoint.parent.kpt_names[keypoint.index]
        self.keypoint_label = QLabel(pretty_text(keypoint_name))
        self.installEventFilter(self)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.keypoint_label)
        self.layout().setContentsMargins(0, 0, 0, 0)

    def on_mouse_press(self, event: QMouseEvent) -> None:
        canvas = self.parent.canvas

        if self.keypoint.visible:
            if canvas.keypoint_annotator.active:
                canvas.keypoint_annotator.end()

            canvas.on_keypoint_left_press(self.keypoint, event)
            canvas.update()

        else:
            if not canvas.keypoint_annotator.active:
                canvas.set_annotating_state(
                    AnnotatingState.DRAWING_KEYPOINTS)

            canvas.keypoint_annotator.set_index(self.keypoint.index)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() in (event.Type.MouseButtonPress,
                            event.Type.MouseButtonDblClick):
            self.on_mouse_press(event)
            return True

        elif event.type() == event.Type.Enter:
            self.keypoint.hovered = True
            self.parent.canvas.update()
            self.update()

        elif event.type() == event.Type.Leave:
            self.keypoint.hovered = False
            self.parent.canvas.update()
            self.update()

        return False

    def update(self) -> None:
        if self.keypoint not in self.keypoint.parent.keypoints:
            return  # This can happen on anno rename, before list is redrawn

        annotator = self.parent.canvas.keypoint_annotator
        hovered = (annotator.label_index == self.keypoint.index
                   and annotator.active) or self.underMouse()

        background = (53, 53, 53) if hovered or self.keypoint.selected \
            or hovered else (33, 33, 33)

        color = (255, 255, 255) if hovered and self.keypoint.selected \
            else (200, 200, 200) if self.keypoint.visible else (82, 82, 82)

        self.keypoint_label.setStyleSheet(f'''
            background-color: rgb{background};
            color: rgb{color};
        ''')


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
        layout.setContentsMargins(1, 0, 0, 0)

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
            source.setStyleSheet('background-color: rgb(33, 33, 33);')

        return False


class UnpinButton(QLabel):
    def __init__(self, parent: AnnotationList) -> None:
        super().__init__('\u276E')
        self.parent = parent

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.parent.setVisible(not self.parent.isVisible())


class CopyImageButton(QLabel):
    def __init__(self, parent: AnnotationList) -> None:
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
    def __init__(self, parent: AnnotationList) -> None:
        super().__init__(parent.parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
