from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel

from app.enums.canvas import AnnotatingState
from app.objects import Annotation, Keypoint
from app.utils import pretty_text
from app.widgets.context_menu import ContextCheckBox

if TYPE_CHECKING:
    from annotator import MainWindow
    from app.canvas import Canvas


class AnnotationList(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent

        self.main_layout = QVBoxLayout(self)
        self.anno_layout = QVBoxLayout()

        self.main_layout.addStretch()
        self.main_layout.addLayout(self.anno_layout)
        self.main_layout.addStretch()
        self.main_layout.addWidget(UnpinButton(self))

        self.main_layout.setContentsMargins(0, 0, 0, 0)
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

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        canvas = self.parent.canvas

        if event.type() in (event.Type.MouseButtonPress,
                            event.Type.MouseButtonDblClick):
            left_clicked = Qt.MouseButton.LeftButton & event.button()

            if left_clicked and self.keypoint.visible:
                canvas.on_keypoint_left_press(self.keypoint, event)
                canvas.update()

        elif event.type() == event.Type.MouseButtonRelease:
            if not self.keypoint.visible:
                canvas.set_annotating_state(AnnotatingState.DRAWING_KEYPOINTS)
                canvas.keypoint_annotator.set_index(self.keypoint.index)

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


class UnpinButton(QWidget):
    def __init__(self, parent: 'AnnotationList') -> None:
        super().__init__()

        self.parent = parent
        self.installEventFilter(self)

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel('\u276E'))
        layout.setContentsMargins(0, 0, 0, 0)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() == event.Type.MouseButtonPress:
            self.parent.setVisible(False)

        elif event.type() == event.Type.Enter:
            source.setStyleSheet(f'background-color: rgb(53, 53, 53);')

        elif event.type() == event.Type.Leave:
            source.setStyleSheet(f'background-color: rgb(33, 33, 33);')

        return False
