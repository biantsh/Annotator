from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent

if TYPE_CHECKING:
    from app.canvas import Canvas


class MouseHandler:
    def __init__(self, parent: 'Canvas') -> None:
        self.parent = parent

        self.cursor_position = 0, 0
        self.global_position = None

        self.left_clicked = False
        self.right_clicked = False
        self.middle_clicked = False

    def _get_cursor_position(self, event: QMouseEvent) -> tuple[int, int]:
        offset_x, offset_y = self.parent.get_center_offset()
        scale = self.parent.get_scale()

        return (int((event.pos().x() - offset_x) / scale),
                int((event.pos().y() - offset_y) / scale))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        position = event.position()
        pos_x, pos_y = position.x(), position.y()

        if Qt.MouseButton.LeftButton & event.buttons():
            self.left_clicked = True
            self.parent.on_mouse_left_press(event)

        elif Qt.MouseButton.RightButton & event.buttons():
            self.right_clicked = True
            self.parent.on_mouse_right_press(event)

        elif Qt.MouseButton.MiddleButton & event.buttons():
            self.middle_clicked = True
            self.parent.on_mouse_middle_press((pos_x, pos_y))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        prev_cursor_position = self.cursor_position

        self.cursor_position = self._get_cursor_position(event)
        self.global_position = event.globalPosition().toPoint()

        if Qt.MouseButton.LeftButton & event.buttons():
            new_x, new_y = self.cursor_position
            old_x, old_y = prev_cursor_position

            delta_x, delta_y = new_x - old_x, new_y - old_y
            self.parent.on_mouse_left_drag((delta_x, delta_y))

        else:
            self.parent.on_mouse_hover()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        buttons = event.buttons()

        self.left_clicked = bool(Qt.MouseButton.LeftButton & buttons)
        self.right_clicked = bool(Qt.MouseButton.RightButton & buttons)
        self.middle_clicked = bool(Qt.MouseButton.MiddleButton & buttons)

        self.mouseMoveEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        angle_delta = event.angleDelta().y()
        position = event.position()

        if angle_delta > 0:
            self.parent.on_scroll_up((position.x(), position.y()))
        elif angle_delta < 0:
            self.parent.on_scroll_down((position.x(), position.y()))
