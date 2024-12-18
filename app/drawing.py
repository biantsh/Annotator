import math
from typing import TYPE_CHECKING

from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor, QFont

from app.enums.annotation import AnnotatingState, HoverType, HOVER_AREAS
from app.objects import Annotation
from app.utils import clip_value, text_to_color

if TYPE_CHECKING:
    from app.canvas import Canvas


class Drawer:
    @staticmethod
    def _draw_path(painter: QPainter,
                   point_groups: tuple[tuple[tuple[float, float], ...], ...],
                   color: tuple[float, ...]
                   ) -> None:
        pen = QPen(QColor(*color))
        pen.setCosmetic(True)
        pen.setWidth(3)

        painter.setPen(pen)
        line_path = QPainterPath()

        for point_group in point_groups:
            line_path.moveTo(*point_group[0])

            for point in point_group:
                line_path.lineTo(*point)

            line_path.lineTo(*point_group[0])

        painter.drawPath(line_path)

    @staticmethod
    def _draw_rectangle(painter: QPainter,
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

        Drawer._draw_path(painter, (points, ), color)

    @staticmethod
    def _fill_rectangle(painter: QPainter,
                        position: tuple[float, ...],
                        color: tuple[float, ...]
                        ) -> None:
        left, top, right, bot = position

        fill_path = QPainterPath()
        fill_path.moveTo(left, top)

        for point in (right, top), (right, bot), (left, bot), (left, top):
            fill_path.lineTo(*point)

        painter.fillPath(fill_path, QColor(*color))

    @staticmethod
    def _draw_text(painter: QPainter,
                   text: str,
                   font_size: int,
                   position: tuple[float, float],
                   ) -> None:
        painter.setFont(QFont('Arial', font_size))
        painter.drawText(*position, text)

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

        Drawer._draw_path(painter, point_groups, (0, 0, 0, 100))

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
        Drawer._draw_rectangle(painter, position, (0, 0, 0, 100))

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

        position = tuple(annotation.position)
        Drawer._draw_rectangle(painter, position, outline_color)

        if hidden:
            return

        if highlighted or selected or annotation.hovered != HoverType.NONE:
            Drawer.fill_annotation(canvas, painter, annotation)

    @staticmethod
    def fill_annotation(canvas: 'Canvas',
                        painter: QPainter,
                        annotation: Annotation
                        ) -> None:
        # Temporarily unset transforms so that the fill width is unscaled.
        # This does make it so that we have to manually scale the coordinates.
        painter.save()
        painter.resetTransform()

        highlighted = annotation.highlighted or annotation.selected

        color = text_to_color(annotation.label_name)
        left, top, right, bottom = annotation.position

        scale = canvas.get_scale()
        offset_x, offset_y = canvas.get_center_offset()

        left = left * scale + offset_x
        top = top * scale + offset_y
        right = right * scale + offset_x
        bottom = bottom * scale + offset_y

        width = 10
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

        if canvas.annotating_state == AnnotatingState.RESIZING:
            areas_to_fill = areas_to_fill.intersection({'full'})

        for area_name in areas_to_fill:
            fill_coords = area_fill_coords[area_name]
            fill_left, fill_top, fill_right, fill_bottom = fill_coords

            fill_left = clip_value(fill_left, left, right)
            fill_right = clip_value(fill_right, left, right)
            fill_top = clip_value(fill_top, top, bottom)
            fill_bottom = clip_value(fill_bottom, top, bottom)

            position = fill_left, fill_top, fill_right, fill_bottom
            Drawer._fill_rectangle(painter, position, (*color, 100))

        painter.restore()

    @staticmethod
    def draw_zoom_indicator(canvas: 'Canvas',
                            painter: QPainter,
                            zoom_level: float
                            ) -> None:
        painter.save()
        painter.resetTransform()

        outline_color = 255, 255, 255, 128
        fill_color = 33, 33, 33, 130
        padding = 10

        canvas_width = canvas.width()
        canvas_height = canvas.height()
        image_width = canvas.pixmap.width()
        image_height = canvas.pixmap.height()

        canvas_area = canvas_width * canvas_height
        aspect_ratio = image_width / image_height

        overview_height = math.sqrt(0.05 * canvas_area / aspect_ratio)
        overview_width = overview_height * aspect_ratio

        x_min, y_min = canvas_width - padding - overview_width, padding
        x_max, y_max = x_min + overview_width, y_min + overview_height

        offset_x, offset_y = canvas.get_center_offset()
        scale = canvas.get_scale()

        x_min_visible = -offset_x / scale
        y_min_visible = -offset_y / scale
        x_max_visible = (canvas_width - offset_x) / scale
        y_max_visible = (canvas_height - offset_y) / scale

        x_min_visible = clip_value(x_min_visible, 0, image_width)
        y_min_visible = clip_value(y_min_visible, 0, image_height)
        x_max_visible = clip_value(x_max_visible, 0, image_width)
        y_max_visible = clip_value(y_max_visible, 0, image_height)

        outer_rect = x_min, y_min, x_max, y_max
        Drawer._draw_rectangle(painter, outer_rect, outline_color)
        Drawer._fill_rectangle(painter, outer_rect, fill_color)

        x_min_inner = x_min + (x_min_visible / image_width) * overview_width
        y_min_inner = y_min + (y_min_visible / image_height) * overview_height
        x_max_inner = x_min + (x_max_visible / image_width) * overview_width
        y_max_inner = y_min + (y_max_visible / image_height) * overview_height

        inner_rect = x_min_inner, y_min_inner, x_max_inner, y_max_inner
        Drawer._draw_rectangle(painter, inner_rect, outline_color)

        text_x = int(x_min + padding / 2)
        text_y = int(y_max - padding / 2)

        zoom_level = round(zoom_level, 1)
        if zoom_level == int(zoom_level):
            zoom_level = int(zoom_level)

        zoom_text = f'{zoom_level}X'
        Drawer._draw_text(painter, zoom_text, 14, (text_x, text_y))

        painter.restore()
