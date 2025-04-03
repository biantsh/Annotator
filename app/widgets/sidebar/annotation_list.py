import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QMouseEvent, QShowEvent, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel
)

from app.enums.annotation import VisibilityType
from app.enums.canvas import AnnotatingState
from app.objects import Annotation, Keypoint
from app.utils import pretty_text
from app.widgets.context_menu import ContextCheckBox
from app.widgets.sidebar.collapsible_section import CollapsibleSection
from app.widgets.sidebar.control_panel import ControlPanel
from app.widgets.tooltip import Tooltip

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

        self.empty_banner = EmptyBanner()
        self.control_panel = ControlPanel(self)

        self.anno_section = CollapsibleSection('Annotations', False)
        self.hidden_section = CollapsibleSection('Hidden', True)

        self.anno_layout = self.anno_section.content_layout
        self.hidden_layout = self.hidden_section.content_layout

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addStretch()
        main_layout.addWidget(self.empty_banner)
        main_layout.addWidget(self.anno_section)
        main_layout.addWidget(self.hidden_section)
        main_layout.addStretch()
        main_layout.addWidget(self.control_panel)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    @property
    def list_items(self) -> list['ListItem']:
        return self.findChildren(ListItem)

    def redraw_widgets(self) -> None:
        for list_item in self.list_items:
            (list_item.hide(), list_item.deleteLater())

        visibility_handler = self.parent.canvas.visibility_handler
        annotator = self.parent.canvas.keypoint_annotator
        annos = self.parent.canvas.annotations.copy()

        if annotator.active and annotator.annotation not in annos:
            annos.append(annotator.annotation)

        sorted_annos = self._sort(annos)
        num_visible, num_hidden = 0, 0

        for anno in sorted_annos:
            list_item = ListItem(self.parent.canvas, anno)

            if visibility_handler.interactable(anno):
                self.anno_layout.addWidget(list_item)
                list_item.set_hidden(False)
                num_visible += 1

            else:
                self.hidden_layout.addWidget(list_item)
                list_item.set_hidden(True)
                num_hidden += 1

        self.anno_section.setVisible(bool(annos))
        self.anno_section.set_count(num_visible)

        self.hidden_section.setVisible(bool(num_hidden))
        self.hidden_section.set_count(num_hidden)

        self.empty_banner.setHidden(bool(annos))
        self.control_panel.redraw()

    def _sort(self, annotations: list[Annotation]) -> list[Annotation]:
        label_map = self.parent.label_map_controller

        def _get_id(anno: Annotation) -> int:
            return label_map.get_id(anno.label_name) \
                if label_map.contains(anno.label_name) else float('inf')

        return sorted(annotations, key=lambda anno: (
            _get_id(anno), anno.label_name, anno.ref_id))

    def update(self) -> None:
        for list_item in self.list_items:
            list_item.update()

    def showEvent(self, event: QShowEvent) -> None:
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.parent.canvas.keypoint_annotator.active:
            self.parent.canvas.keypoint_annotator.end()


class EmptyBanner(QWidget):
    icon_name = 'robo_bear_waiting.png'

    def __init__(self) -> None:
        super().__init__()

        pixmap = QPixmap(os.path.join(__iconpath__, self.icon_name)) \
            .scaled(72, 96, transformMode=__smooth_transform__)

        icon_label = QLabel()
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        text_label = QLabel('No annotations for\nthis image yet')
        text_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.layout = QVBoxLayout()
        self.layout.addWidget(icon_label)
        self.layout.addWidget(text_label)

        self.setLayout(self.layout)
        self.layout.setSpacing(12)


class ListItem(QWidget):
    def __init__(self, canvas: 'Canvas', annotation: Annotation) -> None:
        super().__init__()

        self.canvas = canvas
        self.annotation = annotation

        self.tooltip = Tooltip(self, 1200, pretty_text(annotation.label_name))
        self.checkbox = ContextCheckBox(self.canvas, self.annotation)
        self.keypoint_list = KeypointList(self, annotation)

        self.arrow = QLabel()
        self.arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
        self.layout.setSpacing(0)

        self.header_layout.setContentsMargins(11, 9, 7, 9)

        self.update()

    def set_hidden(self, hidden: bool) -> None:
        fade_effect = QGraphicsOpacityEffect()
        fade_effect.setOpacity(0.5)

        self.setGraphicsEffect(fade_effect if hidden else None)
        self.setEnabled(not hidden)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() in (event.Type.MouseButtonPress,
                            event.Type.MouseButtonDblClick):
            if not self.isEnabled():
                return True

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
            source.setStyleSheet('background-color: transparent;')
            self.checkbox.on_mouse_leave()

        return False

    def update(self) -> None:
        anno = self.annotation
        selected_annos = self.canvas.selected_annos
        selected_kpts = self.canvas.selected_keypoints
        hide_keypoints = self.canvas.keypoints_hidden

        self.keypoint_list.update()
        self.checkbox.update()

        if hide_keypoints or anno.visible != VisibilityType.VISIBLE:
            arrow_color = 117, 117, 117
            show_kpt_list = False

        else:
            arrow_color = 200, 200, 200
            show_kpt_list = bool(selected_kpts) or selected_annos == [anno]
            show_kpt_list &= all(kpt.parent == anno for kpt in selected_kpts)

        self.arrow.setStyleSheet(f'color: rgb{arrow_color}; padding: 0px;')
        self.arrow.setText('\u276E' if show_kpt_list else '\u276F')
        self.arrow.setVisible(bool(anno.kpt_names))

        if self.keypoint_list.isVisible() != show_kpt_list:
            self.keypoint_list.setVisible(show_kpt_list)

        self.tooltip.enable() if self.checkbox.is_elided \
            else self.tooltip.disable()


class KeypointList(QWidget):
    def __init__(self, parent: ListItem, annotation: Annotation) -> None:
        super().__init__()

        self.hide()
        self.parent = parent
        self.annotation = annotation

        layout = QVBoxLayout(self)
        for keypoint in annotation.keypoints:
            layout.addWidget(KeypointItem(self.parent, keypoint))

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def update(self) -> None:
        for keypoint_item in self.findChildren(KeypointItem):
            keypoint_item.update()


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

        highlighted = hovered or self.keypoint.selected
        background = 'rgb(53, 53, 53)' if highlighted else 'transparent'

        color = (255, 255, 255) if hovered and self.keypoint.selected \
            else (200, 200, 200) if self.keypoint.visible else (83, 83, 83)

        self.keypoint_label.setStyleSheet(f'''
            background-color: {background};
            color: rgb{color};
        ''')
