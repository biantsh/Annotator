from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import (
    QImageReader,
    QPixmap,
    QPainter,
    QMouseEvent,
    QPaintEvent,
    QAction
)
from PyQt6.QtWidgets import QWidget

from app.drawing import Drawer
from app.enums.annotation import HoverType
from app.menus import AnnotationContextMenu, CanvasContextMenu
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
        self.selected_anno = None

        self.drawer = Drawer()
        self.setMouseTracking(True)

        delete_anno = QAction(parent=self)
        delete_anno.setShortcut('Del')

        delete_anno.triggered.connect(self.delete_annotation)
        self.addAction(delete_anno)

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

    def rename_annotation(self) -> None:
        pass

    def hide_annotation(self) -> None:
        self.selected_anno.hidden = True
        self.update()

    def delete_annotation(self) -> None:
        self.annotations = list(filter(
            lambda anno: not anno.selected, self.annotations))
        self.update()

    def set_selected_annotation(self) -> None:
        for anno in self.annotations:
            anno.selected = False

        self.selected_anno = self.hovered_anno

        if self.selected_anno:
            self.selected_anno.selected = True

    def get_hidden_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if anno.hidden]

    def get_visible_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if not anno.hidden]

    def get_cursor_position(self, event: QMouseEvent) -> tuple[int, int]:
        offset_x, offset_y = self._get_center_offset()
        scale = self.get_max_scale()

        return (int((event.pos().x() - offset_x) / scale),
                int((event.pos().y() - offset_y) / scale))

    def update_cursor(self, event: QMouseEvent) -> None:
        left_clicked = bool(Qt.MouseButton.LeftButton & event.buttons())
        hover_type = self.hovered_anno.hovered \
            if self.hovered_anno else HoverType.NONE

        cursor = Qt.CursorShape.ArrowCursor

        match left_clicked, hover_type:
            case True, HoverType.FULL:
                cursor = Qt.CursorShape.ClosedHandCursor
            case False, HoverType.FULL:
                cursor = Qt.CursorShape.OpenHandCursor
            case _, HoverType.TOP | HoverType.BOTTOM:
                cursor = Qt.CursorShape.SizeVerCursor
            case _, HoverType.LEFT | HoverType.RIGHT:
                cursor = Qt.CursorShape.SizeHorCursor
            case _, HoverType.TOP_LEFT | HoverType.BOTTOM_RIGHT:
                cursor = Qt.CursorShape.SizeFDiagCursor
            case _, HoverType.TOP_RIGHT | HoverType.BOTTOM_LEFT:
                cursor = Qt.CursorShape.SizeBDiagCursor

        self.setCursor(cursor)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        cursor_position = self.get_cursor_position(event)
        annotations = self.get_visible_annotations()

        if Qt.MouseButton.LeftButton & event.buttons():
            if self.hovered_anno:
                self.drawer.move_annotation(
                    self, self.hovered_anno, cursor_position)

        else:
            self.hovered_anno = self.drawer.set_hovered_annotation(
                self, annotations, cursor_position)

        self.update_cursor(event)
        self.drawer.cursor_position = cursor_position

    def mousePressEvent(self, event: QMouseEvent) -> None:
        cursor_position = self.get_cursor_position(event)
        annotations = self.get_visible_annotations()

        self.hovered_anno = self.drawer.set_hovered_annotation(
            self, annotations, cursor_position)

        self.update_cursor(event)
        self.drawer.cursor_position = cursor_position

        if Qt.MouseButton.LeftButton & event.buttons():
            self.mouseLeftPressEvent()
        elif Qt.MouseButton.RightButton & event.buttons():
            self.mouseRightPressEvent(event)

    def mouseLeftPressEvent(self) -> None:
        self.set_selected_annotation()

    def mouseRightPressEvent(self, event: QMouseEvent) -> None:
        if self.hovered_anno:
            self.set_selected_annotation()
            context_menu = AnnotationContextMenu(self)

        else:
            context_menu = CanvasContextMenu(self)

        context_menu.exec(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.mouseMoveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHints(__antialiasing__ | __pixmap_transform__)

        painter.translate(QPoint(*self._get_center_offset()))
        painter.scale(*[self.get_max_scale()] * 2)

        painter.drawPixmap(0, 0, self.pixmap)

        for annotation in self.get_visible_annotations():
            Drawer.draw_annotation(self, painter, annotation)
