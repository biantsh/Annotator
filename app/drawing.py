from typing import TYPE_CHECKING

from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor

from app.enums.annotation import HoverType, HOVER_AREAS
from app.objects import Annotation
from app.utils import clip_value, text_to_color

if TYPE_CHECKING:
    from app.canvas import Canvas


class Drawer:
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

        line_width = round(2 / canvas.get_scale())
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

        width = round(12 / canvas.get_scale())
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

            left = clip_value(left, annotation.left, annotation.right)
            right = clip_value(right, annotation.left, annotation.right)
            top = clip_value(top, annotation.top, annotation.bottom)
            bot = clip_value(bot, annotation.top, annotation.bottom)

            fill_path = QPainterPath()
            fill_path.moveTo(left, top)

            for point in (right, top), (right, bot), (left, bot), (left, top):
                fill_path.lineTo(*point)

            painter.fillPath(fill_path, QColor(*color, 100))
