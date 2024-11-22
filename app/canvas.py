import hashlib
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import (
    QImageReader,
    QPixmap,
    QPainter,
    QPainterPath,
    QPen,
    QColor,
    QMouseEvent,
    QPaintEvent
)
from PyQt6.QtWidgets import QWidget

from app.objects import Annotation

if TYPE_CHECKING:
    from annotator import MainWindow

__antialiasing__ = QPainter.RenderHint.Antialiasing
__pixmap_transform__ = QPainter.RenderHint.SmoothPixmapTransform


class Canvas(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.annotations = []

        self.setMouseTracking(True)

    def _get_center_offset(self) -> tuple[int, int]:
        canvas = super().size()
        image = self.pixmap

        scale = self.get_max_scale()
        offset_x = (canvas.width() - image.width() * scale) / 2
        offset_y = (canvas.height() - image.height() * scale) / 2

        return int(offset_x), int(offset_y)

    def get_max_scale(self) -> float:
        if self.pixmap.isNull():
            return 1.0

        canvas = super().size()
        image = self.pixmap

        canvas_aspect = canvas.width() / canvas.height()
        image_aspect = image.width() / image.height()

        if canvas_aspect < image_aspect:
            return canvas.width() / image.width()

        return canvas.height() / image.height()

    def reset(self) -> None:
        self.pixmap = QPixmap()
        self.annotations = []
        self.update()

    def load_image(self, image_path: str) -> None:
        image = QImageReader(image_path).read()
        self.pixmap = QPixmap.fromImage(image)
        self.update()

    def load_annotations(self, annotations: list[Annotation]) -> None:
        self.annotations = annotations
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        offset_x, offset_y = self._get_center_offset()
        scale = self.get_max_scale()

        mouse_position = ((event.pos().x() - offset_x) / scale,
                          (event.pos().y() - offset_y) / scale)

        highlighted = False

        for annotation in self.annotations[::-1]:  # Prioritize newer annos
            if annotation.contains_point(mouse_position) and not highlighted:
                highlighted = True
                annotation.hovered = True
            else:
                annotation.hovered = False

        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHints(__antialiasing__ | __pixmap_transform__)

        painter.translate(QPoint(*self._get_center_offset()))
        painter.scale(*[self.get_max_scale()] * 2)

        painter.drawPixmap(0, 0, self.pixmap)

        for annotation in self.annotations:
            CanvasDrawer.draw_annotation(self, painter, annotation)


class CanvasDrawer:
    @staticmethod
    def draw_annotation(canvas: Canvas,
                        painter: QPainter,
                        annotation: Annotation
                        ) -> None:
        color = CanvasDrawer.integer_to_color(annotation.category_id)
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

        if annotation.hovered:
            painter.fillPath(line_path, QColor(*color, 100))

    @staticmethod
    def integer_to_color(integer: int) -> tuple[int, int, int]:
        integer = str(integer).encode('utf-8')
        hash_code = int(hashlib.sha256(integer).hexdigest(), 16)

        red = hash_code % 255
        green = (hash_code // 255) % 255
        blue = (hash_code // 65025) % 255

        return red, green, blue
