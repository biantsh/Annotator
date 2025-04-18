from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent, QKeyEvent
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from app.enums.canvas import AnnotatingState
from app.objects import Annotation
from app.utils import clip_value, pretty_text

if TYPE_CHECKING:
    from app.canvas import Canvas

__mouse_events__ = Qt.WidgetAttribute.WA_TransparentForMouseEvents
__styled_background__ = Qt.WidgetAttribute.WA_StyledBackground


class KeypointAnnotator:
    color_left = 57, 109, 191
    color_right = 153, 46, 46
    color_default = 220, 220, 220
    color_disabled = 100, 100, 100

    def __init__(self, canvas: 'Canvas') -> None:
        super().__init__()
        self.canvas = canvas

        self.keypoint_label = KeypointLabel(canvas)
        self.keypoint_label.hide()

        self.annotation = None
        self.active = False

        self.label_index = 0
        self.kpt_names = []
        self.colors = []

        self.created_keypoints = []

    def begin(self, annotation: Annotation) -> None:
        self.kpt_names = annotation.kpt_names
        self.annotation = annotation

        self.created_keypoints = []
        self.label_index = 0
        self.active = True

        self.colors = [self.color_default] * len(self.kpt_names)
        for left, right in annotation.label_schema.kpt_symmetry:
            self.colors[left - 1] = self.color_left
            self.colors[right - 1] = self.color_right

        text_width = (self.keypoint_label.font_metrics.horizontalAdvance(
            pretty_text(kpt_name)) for kpt_name in self.kpt_names)
        self.keypoint_label.set_width(max(text_width) + 12)

        self.init_label()
        self.keypoint_label.show()

        self.canvas.set_selected_annotation(annotation)

        if annotation not in self.canvas.annotations:
            self.canvas.parent.annotation_list.redraw_widgets()

        self.update()
        self.canvas.update()

    def update(self) -> None:
        mouse_pos = self.canvas.mouse_handler.global_position
        mouse_pos = self.canvas.mapFromGlobal(mouse_pos)

        self.keypoint_label.move(mouse_pos + QPoint(15, 15))

    def set_index(self, index: int) -> None:
        max_index = len(self.kpt_names) - 1

        self.label_index = clip_value(index, 0, max_index)
        keypoint = self.annotation.keypoints[self.label_index]

        self.keypoint_label.set_text(self.kpt_names[self.label_index])
        self.keypoint_label.set_color(self.color_disabled if keypoint.visible
                                      else self.colors[self.label_index])

        self.keypoint_label.set_enabled_prev(self.label_index > 0)
        self.keypoint_label.set_enabled_next(self.label_index < max_index)

        self.canvas.parent.annotation_list.update()

    def next_label(self) -> None:
        self.set_index(self.label_index + 1)

    def prev_label(self) -> None:
        self.set_index(self.label_index - 1)

    def init_label(self) -> None:
        keypoints = self.annotation.keypoints
        self.reset_label()

        for index in range(1, len(keypoints)):
            if not keypoints[index].visible \
                    and keypoints[index - 1].visible:
                self.set_index(index)

    def reset_label(self) -> None:
        for keypoint in self.annotation.keypoints[::-1]:
            if not keypoint.visible:
                self.label_index = keypoint.index

        self.set_index(self.label_index)

    def add_keypoint(self) -> None:
        keypoint = self.annotation.keypoints[self.label_index]
        mouse_pos = self.canvas.mouse_handler.cursor_position

        if keypoint.visible:
            return

        self.created_keypoints.append(keypoint)
        keypoint.position = list(mouse_pos)
        keypoint.visible = True

        if keypoint == self.annotation.keypoints[-1]:
            self.end()
        else:
            self.next_label()

    def on_mouse_press(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and \
                all(kpt.visible for kpt in self.annotation.keypoints):
            self.end()

    def on_key_press(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Return:
            self.end()

        elif event.key() == Qt.Key.Key_Space:
            self.reset_label()

    def end(self) -> None:
        self.active = False
        self.keypoint_label.hide()

        self.canvas.set_annotating_state(AnnotatingState.IDLE)
        self.canvas.on_keypoints_created()

        self.canvas.parent.annotation_list.redraw_widgets()
        self.canvas.on_mouse_hover()


class KeypointLabel(QWidget):
    color_enabled = 220, 220, 220
    color_disabled = 100, 100, 100

    def __init__(self, canvas: 'Canvas') -> None:
        super().__init__(canvas)

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.text_label = QLabel()
        self.left_arrow = QLabel('\u276E')
        self.right_arrow = QLabel('\u276F')

        for label in self.left_arrow, self.text_label, self.right_arrow:
            layout.addWidget(label)

        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.font_metrics = self.text_label.fontMetrics()

        self.setAttribute(__mouse_events__, True)
        self.setAttribute(__styled_background__, True)

    def get_width(self, text: str) -> None:
        return self.font_metrics.horizontalAdvance(pretty_text(text))

    def set_width(self, width: int) -> None:
        self.text_label.setFixedWidth(width)

    def set_text(self, text: str) -> None:
        self.text_label.setText(pretty_text(text))

    def set_color(self, color: tuple[int, ...]) -> None:
        self.text_label.setStyleSheet(f'''
            color: rgb{color};
            font-weight: bold;
        ''')

    def set_enabled_next(self, enabled: bool) -> None:
        color = self.color_enabled if enabled else self.color_disabled
        self.right_arrow.setStyleSheet(f'color: rgb{color};')

    def set_enabled_prev(self, enabled: bool) -> None:
        color = self.color_enabled if enabled else self.color_disabled
        self.left_arrow.setStyleSheet(f'color: rgb{color};')
