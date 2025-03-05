import math
from typing import Sequence, TYPE_CHECKING

from app.controllers.label_map_controller import LabelMapController
from app.enums.annotation import HoverType, SelectionType, VisibilityType
from app.enums.canvas import AnnotatingState
from app.objects import Annotation
from app.utils import text_to_color, clip_value

from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF
from PyQt6.QtGui import (
    QPen,
    QBrush,
    QFont,
    QColor,
    QPixmap,
    QPainter,
    QPainterPath
)

if TYPE_CHECKING:
    from app.canvas import Canvas

__antialiasing__ = QPainter.RenderHint.Antialiasing
__pixmap_transform__ = QPainter.RenderHint.SmoothPixmapTransform


class CanvasPainter(QPainter):
    def __init__(self, parent: 'Canvas') -> None:
        super().__init__()

        self.canvas = parent
        self.anno_painter = AnnotationPainter(self)

        self.begin(parent)
        self.setRenderHints(__antialiasing__ | __pixmap_transform__)

        self.pen = QPen()
        self.pen.setCosmetic(True)
        self.pen.setWidth(3)

        self.brush = QBrush()
        self.font = QFont('Arial', 14)

        self.setPen(self.pen)
        self.setBrush(self.brush)
        self.setFont(self.font)

        self._scale = parent.get_scale()
        self._offsets = parent.get_center_offset()

    def set_fill_color(self, color: Sequence[int] | None) -> None:
        self.brush.setStyle(Qt.BrushStyle.NoBrush)

        if color:
            self.brush.setStyle(Qt.BrushStyle.SolidPattern)
            self.brush.setColor(QColor(*color))

        self.setBrush(self.brush)

    def set_outline_color(self, color: Sequence[int]) -> None:
        self.pen.setColor(QColor(*color))
        self.setPen(self.pen)

    def scale_point(self, coordinates: Sequence[int]) -> tuple[int, ...]:
        pos_x, pos_y = coordinates

        pos_x = int(pos_x * self._scale + self._offsets[0])
        pos_y = int(pos_y * self._scale + self._offsets[1])

        return pos_x, pos_y

    def scale_box(self, coordinates: Sequence[int]) -> tuple[int, ...]:
        left, top, right, bot = coordinates

        top = int(top * self._scale + self._offsets[1])
        bot = int(bot * self._scale + self._offsets[1])
        left = int(left * self._scale + self._offsets[0])
        right = int(right * self._scale + self._offsets[0])

        return left, top, right, bot

    def draw_pixmap(self, pixmap: QPixmap) -> None:
        self.translate(QPoint(*self._offsets))
        self.scale(*[self._scale] * 2)

        self.drawPixmap(0, 0, pixmap)
        self.resetTransform()

    def draw_crosshair(self, cursor_position: tuple[int, int]) -> None:
        pos_x, pos_y = self.scale_point(cursor_position)
        self.set_outline_color((0, 0, 0, 100))

        width, height = self.canvas.width(), self.canvas.height()
        offset_x, offset_y = self._offsets

        self.drawLine(pos_x, offset_y, pos_x, height - offset_y)
        self.drawLine(offset_x, pos_y, width - offset_x, pos_y)

    def draw_candidate_anno(self, position: tuple[int, ...]) -> None:
        left, top, right, bot = self.scale_box(position)
        self.set_outline_color((0, 0, 0, 100))

        width, height = self.canvas.width(), self.canvas.height()
        offset_x, offset_y = self._offsets

        left = clip_value(left, offset_x, width - offset_x)
        right = clip_value(right, offset_x, width - offset_x)
        top = clip_value(top, offset_y, height - offset_y)
        bot = clip_value(bot, offset_y, height - offset_y)

        self.drawRect(QRectF(QPointF(left, top), QPointF(right, bot)))

    def draw_candidate_keypoint(self, position: tuple[int, int]) -> None:
        pos_x, pos_y = self.scale_point(position)

        width, height = self.canvas.width(), self.canvas.height()
        offset_x, offset_y = self._offsets

        pos_x = clip_value(pos_x, offset_x, width - offset_x)
        pos_y = clip_value(pos_y, offset_y, height - offset_y)

        label_schema = self.canvas.keypoint_annotator.annotation.label_schema
        anno_color = text_to_color(label_schema.label_name)

        self.set_fill_color(anno_color)
        self.set_outline_color((*anno_color, 155))

        self.drawEllipse(pos_x - 5, pos_y - 5, 10, 10)
        self.set_fill_color(None)

    def draw_zoom_indicator(self, zoom_level: float) -> None:
        image_width = self.canvas.pixmap.width()
        image_height = self.canvas.pixmap.height()
        width = self.canvas.width()
        height = self.canvas.height()

        aspect_ratio = image_width / image_height
        overview_height = math.sqrt(0.05 * width * height / aspect_ratio)
        overview_width = overview_height * aspect_ratio

        x_min, y_min = width - overview_width - 10, 10
        outer_rect = QRectF(x_min, y_min, overview_width, overview_height)

        self.set_outline_color((255, 255, 255, 128))
        self.fillRect(outer_rect, QColor(33, 33, 33, 130))
        self.drawRect(outer_rect)

        scale = self._scale
        offset_x, offset_y = self._offsets

        x_min_vis = clip_value(-offset_x / scale, 0, image_width)
        y_min_vis = clip_value(-offset_y / scale, 0, image_height)
        x_max_vis = clip_value((width - offset_x) / scale, 0, image_width)
        y_max_vis = clip_value((height - offset_y) / scale, 0, image_height)

        x_min_inner = x_min + x_min_vis * overview_width / image_width
        y_min_inner = y_min + y_min_vis * overview_height / image_height
        x_max_inner = x_min + x_max_vis * overview_width / image_width
        y_max_inner = y_min + y_max_vis * overview_height / image_height

        self.drawRect(QRectF(QPointF(x_min_inner, y_min_inner),
                             QPointF(x_max_inner, y_max_inner)))

        text_x = int(x_min + 5)
        text_y = int(overview_height + 5)

        zoom_level = round(zoom_level, 1)
        if zoom_level == int(zoom_level):
            zoom_level = int(zoom_level)

        self.drawText(QPointF(text_x, text_y), f'{zoom_level}X')

    def draw_brightness_indicator(self, step: int) -> None:
        self.setPen(QColor(200, 200, 200, 255))
        text = f'Brightness amplification: {step * 5}%'

        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text)
        text_height = font_metrics.height()

        pos_x = self.canvas.width() - text_width - 26
        pos_y = self.canvas.height() - text_height - 26
        outer_rect = QRectF(pos_x, pos_y, text_width + 16, text_height + 16)

        self.set_outline_color((255, 255, 255, 128))
        self.fillRect(outer_rect, QColor(33, 33, 33, 130))
        self.drawRect(outer_rect)

        text_x = pos_x + 8
        text_y = pos_y + font_metrics.ascent() + 8
        self.drawText(QPointF(text_x, text_y), text)

    def paint_scene(self) -> None:
        self.draw_pixmap(self.canvas.pixmap)

        annos_to_draw = self.canvas.annotations.copy()

        if self.canvas.keypoint_annotator.active:
            current_anno = self.canvas.keypoint_annotator.annotation

            if current_anno not in annos_to_draw:
                annos_to_draw.append(current_anno)

        for annotation in annos_to_draw:
            if annotation.visible or annotation.highlighted:
                self.anno_painter.draw_annotation(annotation)

        state = self.canvas.annotating_state
        cursor_position = self.canvas.mouse_handler.cursor_position

        if state == AnnotatingState.READY:
            if self.canvas.is_cursor_in_bounds():
                self.draw_crosshair(cursor_position)

        elif state == AnnotatingState.DRAWING_ANNO:
            self.draw_candidate_anno((*self.canvas.anno_first_corner,
                                      *cursor_position))

        elif state == AnnotatingState.DRAWING_KEYPOINTS \
                and not self.canvas.hovered_keypoint:
            self.draw_candidate_keypoint(cursor_position)

        self.pen.setWidth(2)

        if self.canvas.zoom_handler.draw_indicator:
            self.draw_zoom_indicator(self.canvas.zoom_handler.zoom_level)

        if self.canvas.brightness_handler.draw_indicator:
            self.draw_brightness_indicator(self.canvas.brightness_handler.step)


class AnnotationPainter:
    fill_areas = {
        HoverType.NONE: set(),
        HoverType.FULL: {'full'},
        HoverType.TOP: {'top'},
        HoverType.LEFT: {'left'},
        HoverType.RIGHT: {'right'},
        HoverType.BOTTOM: {'bottom'},
        HoverType.TOP_LEFT: {'top', 'left'},
        HoverType.TOP_RIGHT: {'top', 'right'},
        HoverType.BOTTOM_LEFT: {'bottom', 'left'},
        HoverType.BOTTOM_RIGHT: {'bottom', 'right'}
    }

    def __init__(self, parent: 'CanvasPainter') -> None:
        self.parent = parent

    @property
    def label_map(self) -> LabelMapController:
        return self.parent.canvas.label_map

    def draw_annotation(self, anno: Annotation) -> None:
        drawing_keypoints = self.parent.canvas.keypoint_annotator.active
        highlighted = anno.highlighted or anno.selected

        self.parent.set_outline_color(
            (205, 205, 205, 255)
            if highlighted and not drawing_keypoints
            else (*text_to_color(anno.label_name), 155))

        if not anno.visible:
            return

        if anno.has_bbox:
            left, top, right, bot = self.parent.scale_box(anno.position)
            self.parent.drawRect(left, top, right - left, bot - top)

            if (anno.hovered or highlighted) and not drawing_keypoints:
                self.fill_annotation(anno)

        elif anno.hovered and not drawing_keypoints:
            self.fill_annotation(anno)

        if anno.has_keypoints and anno.visible == VisibilityType.VISIBLE:
            self.draw_keypoint_edges(anno)
            self.draw_keypoints(anno)

    def fill_annotation(self, anno: Annotation) -> None:
        bbox = anno.position if anno.has_bbox else anno.implicit_bbox
        left, top, right, bottom = self.parent.scale_box(bbox)

        width = 10

        area_coords = {
            'full': (left, top, right, bottom),
            'top': (left, top, right, min(top + width, bottom)),
            'left': (left, top, min(left + width, right), bottom),
            'right': (max(right - width, left), top, right, bottom),
            'bottom': (left, max(bottom - width, top), right, bottom)
        }

        fill_areas = self.fill_areas[anno.hovered]

        if (anno.selected or anno.highlighted) and not fill_areas:
            fill_areas = {'full'}

        if self.parent.canvas.annotating_state == AnnotatingState.MOVING_ANNO:
            fill_areas = fill_areas.intersection({'full'})

        fill_path = QPainterPath()
        fill_path.setFillRule(Qt.FillRule.WindingFill)

        for area_name in fill_areas:
            left, top, right, bot = area_coords[area_name]
            fill_path.addRect(QRectF(QPointF(left, top), QPointF(right, bot)))

        if 'full' in fill_areas and any(kpt.selected for kpt in anno.keypoints):
            return

        anno_color = *text_to_color(anno.label_name), 100
        self.parent.fillPath(fill_path, QColor(*anno_color))

    def draw_keypoints(self, anno: Annotation) -> None:
        keypoint_annotator = self.parent.canvas.keypoint_annotator
        annotating = keypoint_annotator.active and \
            keypoint_annotator.annotation == anno

        anno_color = text_to_color(anno.label_name)
        anno_selected = anno.selected in (SelectionType.SELECTED,
                                          SelectionType.NEWLY_SELECTED)

        symmetry = list(zip(*anno.label_schema.kpt_symmetry))
        left_keypoints, right_keypoints = symmetry or ([], [])

        for index, keypoint in enumerate(anno.keypoints, 1):
            if not keypoint.visible:
                continue

            if keypoint.hovered or keypoint.selected:
                fill_color = anno_color
            elif index in left_keypoints:
                fill_color = 57, 109, 191
            elif index in right_keypoints:
                fill_color = 153, 46, 46
            else:
                fill_color = 82, 82, 82

            highlighted = anno_selected or keypoint.selected

            self.parent.set_fill_color(fill_color)
            self.parent.set_outline_color((205, 205, 205, 255)
                                          if highlighted or annotating
                                          else (*anno_color, 155))

            pos_x, pos_y = self.parent.scale_point(keypoint.position)
            self.parent.drawEllipse(pos_x - 5, pos_y - 5, 10, 10)

        self.parent.set_fill_color(None)

    def draw_keypoint_edges(self, anno: Annotation) -> None:
        anno_color = text_to_color(anno.label_name)
        anno_selected = anno.selected in (SelectionType.SELECTED,
                                          SelectionType.NEWLY_SELECTED)

        keypoints, skeleton = anno.keypoints, anno.label_schema.kpt_edges

        for start, end in skeleton:
            kpt_start, kpt_end = keypoints[start - 1], keypoints[end - 1]
            kpt_selected = kpt_start.selected and kpt_end.selected

            if not (kpt_start.visible and kpt_end.visible):
                continue

            highlighted = anno.highlighted or anno_selected or kpt_selected
            annotating = self.parent.canvas.keypoint_annotator.active

            self.parent.set_outline_color(
                (205, 205, 205, 255)
                if highlighted and not annotating
                else (*anno_color, 155))

            start_x, start_y = self.parent.scale_point(kpt_start.position)
            end_x, end_y = self.parent.scale_point(kpt_end.position)
            self.parent.drawLine(start_x, start_y, end_x, end_y)
