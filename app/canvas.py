import copy
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

from app.actions import CanvasActions
from app.drawing import Drawer
from app.enums.annotation import HoverType
from app.widgets.context_menu import AnnotationContextMenu, CanvasContextMenu
from app.objects import Annotation

if TYPE_CHECKING:
    from annotator import MainWindow

__antialiasing__ = QPainter.RenderHint.Antialiasing
__pixmap_transform__ = QPainter.RenderHint.SmoothPixmapTransform


class Canvas(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent

        self.pixmap = QPixmap()
        self.annotations = []

        self.hovered_anno = None
        self.selected_annos = []

        self.drawer = Drawer()
        self.setMouseTracking(True)

        for action in CanvasActions(self).actions.values():
            self.addAction(action)

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

    def get_visible_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if not anno.hidden]

    def get_hidden_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if anno.hidden]

    def hide_annotations(self) -> None:
        should_hide = not any(anno.hidden for anno in self.selected_annos)

        for anno in self.selected_annos:
            anno.hidden = should_hide

        self.update()

    def delete_annotations(self) -> None:
        self.annotations = list(filter(
            lambda anno: not anno.selected, self.annotations))

        self.update()

    def copy_annotations(self) -> None:
        all_annotations = self.annotations[::-1]

        selected = [anno for anno in all_annotations if anno.selected]
        to_copy = selected or all_annotations

        self.parent.annotation_controller.clipboard = copy.deepcopy(to_copy)

    def paste_annotations(self) -> None:
        pasted_annotations = self.parent.annotation_controller.clipboard
        pasted_annotations = copy.deepcopy(pasted_annotations)

        for annotation in pasted_annotations:
            annotation.hovered = HoverType.NONE
            annotation.selected = True
            annotation.hidden = False

        for annotation in self.annotations:
            annotation.selected = False

        # Add pasted annotations in the same order they were selected
        self.annotations.extend(pasted_annotations[::-1])
        self.selected_annos = pasted_annotations

        self.update()

    def rename_annotations(self) -> None:
        pass

    def set_selected_annotation(self) -> None:
        for anno in self.annotations:
            anno.selected = False

        self.selected_annos = []
        self.add_selected_annotation()

    def add_selected_annotation(self) -> None:
        if not self.hovered_anno or self.hovered_anno in self.selected_annos:
            return

        self.selected_annos.append(self.hovered_anno)
        self.hovered_anno.selected = True

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
            self.mouseLeftPressEvent(event)
        elif Qt.MouseButton.RightButton & event.buttons():
            self.mouseRightPressEvent(event)

    def mouseLeftPressEvent(self, event: QMouseEvent) -> None:
        if Qt.KeyboardModifier.ControlModifier & event.modifiers():
            self.add_selected_annotation()
        else:
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

    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHints(__antialiasing__ | __pixmap_transform__)

        painter.translate(QPoint(*self._get_center_offset()))
        painter.scale(*[self.get_max_scale()] * 2)

        painter.drawPixmap(0, 0, self.pixmap)

        for annotation in self.get_visible_annotations():
            Drawer.draw_annotation(self, painter, annotation)
