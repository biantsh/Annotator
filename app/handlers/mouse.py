from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent

if TYPE_CHECKING:
    from app.canvas import Canvas


class MouseHandler:
    def __init__(self, parent: 'Canvas') -> None:
        self.parent = parent
        self.last_cursor_position = None

    def _get_cursor_position(self, event: QMouseEvent) -> tuple[int, int]:
        offset_x, offset_y = self.parent.get_center_offset()
        scale = self.parent.get_scale()

        return (int((event.pos().x() - offset_x) / scale),
                int((event.pos().y() - offset_y) / scale))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        cursor_position = self._get_cursor_position(event)
        self.last_cursor_position = cursor_position

        self.parent.set_cursor_icon(event)

        if Qt.MouseButton.LeftButton & event.buttons():
            self.parent.on_mouse_left_press(event)
        elif Qt.MouseButton.RightButton & event.buttons():
            self.parent.on_mouse_right_press(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        cursor_position = self._get_cursor_position(event)

        if Qt.MouseButton.LeftButton & event.buttons():
            if self.last_cursor_position:
                old_x, old_y = self.last_cursor_position
                new_x, new_y = cursor_position

                delta_x, delta_y = new_x - old_x, new_y - old_y
                self.parent.on_mouse_left_drag((delta_x, delta_y))
        else:
            self.parent.on_mouse_hover(cursor_position)

        self.last_cursor_position = cursor_position
        self.parent.set_cursor_icon(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.mouseMoveEvent(event)
