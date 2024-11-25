from typing import TYPE_CHECKING

from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor

from app.enums.annotation import HoverType, HOVER_AREAS
from app.objects import Annotation
from app.utils import text_to_color

if TYPE_CHECKING:
    from app.canvas import Canvas


class Drawer:
    def __init__(self) -> None:
        self.cursor_position = None

    def move_annotation(self,
                        canvas: 'Canvas',
                        annotation: Annotation,
                        mouse_position: tuple[int, int]
                        ) -> None:
        if self.cursor_position is None:
            return

        old_x, old_y = self.cursor_position
        new_x, new_y = mouse_position

        delta_x, delta_y = new_x - old_x, new_y - old_y
        x_min, y_min, x_max, y_max = annotation.position

        hover_type = annotation.hovered

        right_border, left_border = canvas.pixmap.width(), 0
        bottom_border, top_border = canvas.pixmap.height(), 0

        if ((delta_x > 0 and x_max + delta_x < right_border) or
                (delta_x < 0 and x_min + delta_x > left_border)):
            if hover_type & HoverType.LEFT or hover_type == HoverType.FULL:
                x_min += delta_x
            if hover_type & HoverType.RIGHT or hover_type == HoverType.FULL:
                x_max += delta_x

        if ((delta_y > 0 and y_max + delta_y < bottom_border) or
                (delta_y < 0 and y_min + delta_y > top_border)):
            if hover_type & HoverType.TOP or hover_type == HoverType.FULL:
                y_min += delta_y
            if hover_type & HoverType.BOTTOM or hover_type == HoverType.FULL:
                y_max += delta_y

        # Flip the left/right and top/bottom hover types
        if x_min > x_max:
            annotation.hovered += HoverType.LEFT \
                if hover_type & HoverType.LEFT else -HoverType.LEFT
        if y_min > y_max:
            annotation.hovered += HoverType.TOP \
                if hover_type & HoverType.TOP else -HoverType.TOP

        x_min, x_max = sorted([x_min, x_max])
        y_min, y_max = sorted([y_min, y_max])

        annotation.position = x_min, y_min, x_max, y_max

    @staticmethod
    def draw_annotation(canvas: 'Canvas',
                        painter: QPainter,
                        annotation: Annotation
                        ) -> None:
        highlighted = annotation.highlighted or annotation.selected

        if highlighted:
            outline_color = 255, 255, 255
            opacity = 255
        else:
            outline_color = text_to_color(annotation.label_name)
            opacity = 155

        pen = QPen(QColor(*outline_color, opacity))

        line_width = round(2 / canvas.get_max_scale())
        line_width = max(line_width, 2)

        pen.setWidth(line_width)
        painter.setPen(pen)

        line_path = QPainterPath()
        line_path.moveTo(*annotation.points[0])

        for point in annotation.points:
            line_path.lineTo(*point)

        line_path.lineTo(*annotation.points[0])
        painter.drawPath(line_path)

        if highlighted or annotation.hovered != HoverType.NONE:
            Drawer.fill_annotation(canvas, painter, annotation)

    @staticmethod
    def fill_annotation(canvas: 'Canvas',
                        painter: QPainter,
                        annotation: Annotation
                        ) -> None:
        highlighted = annotation.highlighted or annotation.selected

        color = text_to_color(annotation.label_name)
        left, top, right, bottom = annotation.position

        width = round(12 / canvas.get_max_scale())
        width = max(width, 8)

        area_fill_coords = {
            'full': [left, top, right, bottom],
            'top': [left + width, top, right - width, top + width],
            'left': [left, top + width, left + width, bottom - width],
            'right': [right - width, top + width, right, bottom - width],
            'bottom': [left + width, bottom - width, right - width, bottom],
            'top_left': [left, top, left + width, top + width],
            'top_right': [right - width, top, right, top + width],
            'bottom_left': [left, bottom - width, left + width, bottom],
            'bottom_right': [right - width, bottom - width, right, bottom]
        }

        areas_to_fill = set()

        for hover_type, areas in HOVER_AREAS.items():
            if annotation.hovered & hover_type:
                areas_to_fill.update(areas)

        if highlighted and not areas_to_fill:
            areas_to_fill.add('full')

        for area_name in areas_to_fill:
            left, top, right, bot = area_fill_coords[area_name]

            fill_path = QPainterPath()
            fill_path.moveTo(left, top)

            for point in (right, top), (right, bot), (left, bot), (left, top):
                fill_path.lineTo(*point)

            painter.fillPath(fill_path, QColor(*color, 100))

    @staticmethod
    def set_hovered_annotation(canvas: 'Canvas',
                               annotations: list[Annotation],
                               mouse_position: tuple[int, int]
                               ) -> Annotation | None:
        hovered = None

        edge_width = round(8 / canvas.get_max_scale())
        edge_width = max(edge_width, 4)

        for annotation in annotations[::-1]:  # Prioritize newer annos
            hovered_type = annotation.get_hovered(mouse_position, edge_width)
            annotation.hovered = HoverType.NONE

            if hovered_type != HoverType.NONE and hovered is None:
                annotation.hovered = hovered_type
                hovered = annotation

        return hovered
