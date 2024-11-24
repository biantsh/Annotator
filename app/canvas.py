from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import (
    QImageReader,
    QPixmap,
    QPainter,
    QMouseEvent,
    QPaintEvent
)
from PyQt6.QtWidgets import QWidget

from app.drawing import Drawer
from app.enums.annotation import HoverType
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
        self.hovered_anno = None

        self.drawer = Drawer()
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

    def set_cursor_shape(self,
                         hover_type: HoverType,
                         left_clicked: bool
                         ) -> None:
        cursor = Qt.CursorShape.ArrowCursor

        match hover_type, left_clicked:
            case HoverType.FULL, True:
                cursor = Qt.CursorShape.ClosedHandCursor
            case HoverType.FULL, False:
                cursor = Qt.CursorShape.OpenHandCursor
            case HoverType.TOP | HoverType.BOTTOM, _:
                cursor = Qt.CursorShape.SizeVerCursor
            case HoverType.LEFT | HoverType.RIGHT, _:
                cursor = Qt.CursorShape.SizeHorCursor
            case HoverType.TOP_LEFT | HoverType.BOTTOM_RIGHT, _:
                cursor = Qt.CursorShape.SizeFDiagCursor
            case HoverType.TOP_RIGHT | HoverType.BOTTOM_LEFT, _:
                cursor = Qt.CursorShape.SizeBDiagCursor

        self.setCursor(cursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        offset_x, offset_y = self._get_center_offset()
        scale = self.get_max_scale()

        left_clicked = bool(Qt.MouseButton.LeftButton & event.buttons())
        mouse_position = ((event.pos().x() - offset_x) / scale,
                          (event.pos().y() - offset_y) / scale)

        if left_clicked:
            if self.hovered_anno:
                self.drawer.move_annotation(
                    self, self.hovered_anno, mouse_position)

        else:
            self.hovered_anno = self.drawer.set_hovered_annotation(
                self, self.annotations, mouse_position)

        hover_type = self.hovered_anno.hovered \
            if self.hovered_anno else HoverType.NONE
        self.set_cursor_shape(hover_type, left_clicked)

        self.update()
        self.drawer.mouse_position = mouse_position

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.mouseMoveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHints(__antialiasing__ | __pixmap_transform__)

        painter.translate(QPoint(*self._get_center_offset()))
        painter.scale(*[self.get_max_scale()] * 2)

        painter.drawPixmap(0, 0, self.pixmap)

        for annotation in self.annotations:
            Drawer.draw_annotation(self, painter, annotation)
