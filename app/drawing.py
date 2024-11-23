import hashlib
from typing import TYPE_CHECKING

from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor

from app.enums.annotation import HoverType, HOVER_AREAS
from app.objects import Annotation

if TYPE_CHECKING:
    from app.canvas import Canvas


class Drawer:
    def __init__(self) -> None:
        self.mouse_position = None

    def move_annotation(self,
                        annotation: Annotation,
                        mouse_position: tuple[int, int]
                        ) -> None:
        if self.mouse_position is None:
            return

        old_x, old_y = self.mouse_position
        new_x, new_y = mouse_position

        delta_x, delta_y = new_x - old_x, new_y - old_y
        x_min, y_min, x_max, y_max = annotation.position

        hover_type = annotation.hovered

        if hover_type & HoverType.TOP or hover_type == HoverType.FULL:
            y_min += delta_y
        if hover_type & HoverType.LEFT or hover_type == HoverType.FULL:
            x_min += delta_x
        if hover_type & HoverType.RIGHT or hover_type == HoverType.FULL:
            x_max += delta_x
        if hover_type & HoverType.BOTTOM or hover_type == HoverType.FULL:
            y_max += delta_y

        annotation.position = x_min, y_min, x_max, y_max

    @staticmethod
    def set_hovered_annotation(canvas: 'Canvas',
                               annotations: list[Annotation],
                               mouse_position: tuple[int, int]
                               ) -> Annotation | None:
        hovered = None

        edge_width = round(12 / canvas.get_max_scale())
        edge_width = max(edge_width, 8)

        for annotation in annotations[::-1]:  # Prioritize newer annos
            hovered_type = annotation.get_hovered(mouse_position, edge_width)
            annotation.hovered = HoverType.NONE

            if hovered_type != HoverType.NONE and hovered is None:
                annotation.hovered = hovered_type
                hovered = annotation

        return hovered

    @staticmethod
    def draw_annotation(canvas: 'Canvas',
                        painter: QPainter,
                        annotation: Annotation
                        ) -> None:
        color = Drawer.integer_to_color(annotation.category_id)
        pen = QPen(QColor(*color, 155))

        line_width = round(2 / canvas.get_max_scale())
        line_width = max(line_width, 1)

        pen.setWidth(line_width)
        painter.setPen(pen)

        line_path = QPainterPath()
        line_path.moveTo(*annotation.points[0])

        for point in annotation.points:
            line_path.lineTo(*point)

        line_path.lineTo(*annotation.points[0])
        painter.drawPath(line_path)

        if annotation.hovered != HoverType.NONE:
            Drawer.fill_annotation(canvas, painter, annotation)

    @staticmethod
    def fill_annotation(canvas: 'Canvas',
                        painter: QPainter,
                        annotation: Annotation
                        ) -> None:
        color = Drawer.integer_to_color(annotation.category_id)
        left, top, right, bottom = annotation.position

        width = round(6 / canvas.get_max_scale())
        width = max(width, 4)

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

        for area_name in areas_to_fill:
            left, top, right, bot = area_fill_coords[area_name]

            fill_path = QPainterPath()
            fill_path.moveTo(left, top)

            for point in (right, top), (right, bot), (left, bot), (left, top):
                fill_path.lineTo(*point)

            painter.fillPath(fill_path, QColor(*color, 100))

    @staticmethod
    def integer_to_color(integer: int) -> tuple[int, int, int]:
        integer = str(integer).encode('utf-8')
        hash_code = int(hashlib.sha256(integer).hexdigest(), 16)

        red = hash_code % 255
        green = (hash_code // 255) % 255
        blue = (hash_code // 65025) % 255

        return red, green, blue
