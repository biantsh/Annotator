from typing import TYPE_CHECKING

from app.utils import clip_value

if TYPE_CHECKING:
    from app.canvas import Canvas


class ZoomHandler:
    _min_zoom = 1
    _max_zoom = 7

    def __init__(self, parent: 'Canvas') -> None:
        self.zoom_level = self._min_zoom
        self.parent = parent

        self.pan_x = 0
        self.pan_y = 0

    def _set_zoom(self,
                  zoom_level: float,
                  cursor_position: tuple[float, float]
                  ) -> None:
        x_pos, y_pos = cursor_position

        scale_before = self.parent.get_scale()
        offset_x_before, offset_y_before = self.parent.get_center_offset()

        self.zoom_level = clip_value(zoom_level,
                                     self._min_zoom,
                                     self._max_zoom)

        scale_after = self.parent.get_scale()
        offset_x_after, offset_y_after = self.parent.get_center_offset()

        x_unscaled = (x_pos - offset_x_before) / scale_before
        y_unscaled = (y_pos - offset_y_before) / scale_before

        x_pos_new = x_unscaled * scale_after + offset_x_after
        y_pos_new = y_unscaled * scale_after + offset_y_after

        self.pan_x += x_pos - x_pos_new
        self.pan_y += y_pos - y_pos_new

        self.clip_pan_values()

    def zoom_in(self, cursor_position: tuple[float, float]) -> None:
        self._set_zoom(self.zoom_level + 0.2, cursor_position)

    def zoom_out(self, cursor_position: tuple[float, float]) -> None:
        self._set_zoom(self.zoom_level - 0.2, cursor_position)

    def toggle_zoom(self, cursor_position: tuple[float, float]) -> None:
        if self.zoom_level == self._max_zoom:
            self._set_zoom(self._min_zoom, cursor_position)
            self.pan_x = self.pan_y = 0
        else:
            self._set_zoom(self._max_zoom, cursor_position)

    def reset(self) -> None:
        self.zoom_level = self._min_zoom
        self.pan_x = 0
        self.pan_y = 0

    def clip_pan_values(self) -> None:
        """Clip the pan values to prevent the image from panning off-screen."""
        image = self.parent.pixmap.size()
        scale = self.parent.get_scale()

        scaled_width = image.width() * scale
        scaled_height = image.height() * scale

        pan_bound_x = (scaled_width - (scaled_width // self.zoom_level)) / 2
        pan_bound_y = (scaled_height - (scaled_height // self.zoom_level)) / 2

        self.pan_x = clip_value(self.pan_x, -pan_bound_x, pan_bound_x)
        self.pan_y = clip_value(self.pan_y, -pan_bound_y, pan_bound_y)
