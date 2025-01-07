from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QMouseEvent, QWheelEvent

if TYPE_CHECKING:
    from app.canvas import Canvas


class MouseHandler:
    def __init__(self, parent: 'Canvas') -> None:
        self.parent = parent

        self.cursor_position = 0, 0
        self.global_position = QCursor.pos()

        self.left_clicked = False
        self.double_clicked = False

        self.drag_start_pos = None
        self.drag_start_pan = None

    def _get_cursor_position(self, event: QMouseEvent) -> tuple[int, int]:
        offset_x, offset_y = self.parent.get_center_offset()
        scale = self.parent.get_scale()

        return (int((event.pos().x() - offset_x) / scale),
                int((event.pos().y() - offset_y) / scale))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        prev_cursor_position = self.cursor_position

        self.cursor_position = self._get_cursor_position(event)
        self.global_position = event.globalPosition().toPoint()

        if Qt.MouseButton.LeftButton & event.buttons():
            new_x, new_y = self.cursor_position
            old_x, old_y = prev_cursor_position

            delta_x, delta_y = new_x - old_x, new_y - old_y
            self.parent.on_mouse_left_drag((delta_x, delta_y))

        elif Qt.MouseButton.RightButton & event.buttons():
            # Shift is calculated differently here as panning the image uses
            # a different coordinate system compared to dragging an annotation
            current_pos = event.position()

            shift_x = current_pos.x() - self.drag_start_pos.x()
            shift_y = current_pos.y() - self.drag_start_pos.y()

            self.parent.on_mouse_right_drag((shift_x, shift_y))

        else:
            self.parent.on_mouse_hover()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        position = event.position()
        pos_x, pos_y = position.x(), position.y()

        if Qt.MouseButton.LeftButton & event.buttons():
            self.left_clicked = True
            self.parent.on_mouse_left_press(event)

        if Qt.MouseButton.RightButton & event.buttons():
            self.drag_start_pos = event.position()
            self.drag_start_pan = (self.parent.zoom_handler.pan_x,
                                   self.parent.zoom_handler.pan_y)

        if Qt.MouseButton.MiddleButton & event.buttons():
            self.parent.on_mouse_middle_press((pos_x, pos_y))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.parent.keypoint_annotator.active:
            self.parent.keypoint_annotator.on_mouse_press(event)

        elif event.button() == Qt.MouseButton.LeftButton:
            if self.parent.hovered_anno and not self.double_clicked:
                annotator = self.parent.keypoint_annotator

                if annotator.active:
                    if all(kpt.visible for kpt in annotator.annotation.keypoints):
                        self.parent.keypoint_annotator.end()

                else:
                    self.parent.on_annotation_left_press(event)

            self.left_clicked = False
            self.double_clicked = False

        elif event.button() == Qt.MouseButton.RightButton:
            if event.position() == self.drag_start_pos:
                self.parent.on_mouse_right_press(event)

        self.mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent.on_mouse_double_click(event)
            self.double_clicked = True

        else:
            self.parent.mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        angle_delta = event.angleDelta().y()
        position = event.position()

        if angle_delta > 0:
            self.parent.on_scroll_up((position.x(), position.y()))
        elif angle_delta < 0:
            self.parent.on_scroll_down((position.x(), position.y()))
