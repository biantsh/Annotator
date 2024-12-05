from typing import TYPE_CHECKING

from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor

from app.enums.annotation import HoverType, HOVER_AREAS
from app.objects import Annotation
from app.utils import clip_value, text_to_color

if TYPE_CHECKING:
    from app.canvas import Canvas


class Drawer:
    @staticmethod
    def _draw_path(canvas: 'Canvas',
                   painter: QPainter,
                   point_groups: tuple[tuple[tuple[float, float], ...], ...],
                   color: tuple[float, ...]
                   ) -> None:
        pen = QPen(QColor(*color))

        line_width = round(2 / canvas.get_scale())
        line_width = max(line_width, 2)

        pen.setWidth(line_width)
        painter.setPen(pen)

        line_path = QPainterPath()

        for point_group in point_groups:
            line_path.moveTo(*point_group[0])

            for point in point_group:
                line_path.lineTo(*point)

            line_path.lineTo(*point_group[0])

        painter.drawPath(line_path)

    @staticmethod
    def _draw_rectangle(canvas: 'Canvas',
                        painter: QPainter,
                        position: tuple[float, ...],
                        color: tuple[float, ...]
                        ) -> None:
        x_min, y_min, x_max, y_max = position

        points = (
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max),
            (x_min, y_min)
        )

        Drawer._draw_path(canvas, painter, (points, ), color)

    @staticmethod
    def draw_crosshair(canvas: 'Canvas',
                       painter: QPainter,
                       position: tuple[int, int]
                       ) -> None:
        pos_x, pos_y = position
        point_groups = (
            ((pos_x, 0), (pos_x, canvas.pixmap.height()), ),
            ((0, pos_y), (canvas.pixmap.width(), pos_y), )
        )

        Drawer._draw_path(canvas, painter, point_groups, (0, 0, 0, 100))

    @staticmethod
    def draw_candidate_annotation(canvas: 'Canvas',
                                  painter: QPainter,
                                  first_corner: tuple[float, float],
                                  second_corner: tuple[float, float]
                                  ) -> None:
        x_min, y_min = first_corner
        x_max, y_max = second_corner

        x_min = clip_value(x_min, 0, canvas.pixmap.width())
        y_min = clip_value(y_min, 0, canvas.pixmap.height())
        x_max = clip_value(x_max, 0, canvas.pixmap.width())
        y_max = clip_value(y_max, 0, canvas.pixmap.height())

        position = x_min, y_min, x_max, y_max
        Drawer._draw_rectangle(canvas, painter, position, (0, 0, 0, 100))

    @staticmethod
    def draw_annotation(canvas: 'Canvas',
                        painter: QPainter,
                        annotation: Annotation
                        ) -> None:
        hidden = annotation.hidden
        selected = annotation.selected
        highlighted = annotation.highlighted

        if hidden and not highlighted:
            return

        outline_color = (255, 255, 255, 255) if highlighted or selected else \
            [*text_to_color(annotation.label_name), 155]

        position = annotation.position
        Drawer._draw_rectangle(canvas, painter, position, outline_color)

        if hidden:
            return

        if highlighted or selected or annotation.hovered != HoverType.NONE:
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
