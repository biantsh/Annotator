import copy
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import (
    QImageReader,
    QPixmap,
    QPainter,
    QMouseEvent,
    QKeyEvent,
    QPaintEvent
)
from PyQt6.QtWidgets import QWidget

from app.actions import CanvasActions
from app.drawing import Drawer
from app.enums.annotation import HoverType
from app.handlers.keyboard import KeyboardHandler
from app.handlers.mouse import MouseHandler
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
        self.drawer = Drawer()

        self.annotations = []
        self.selected_annos = []
        self.hovered_anno = None

        self.mouse_handler = MouseHandler(self)
        self.keyboard_handler = KeyboardHandler(self)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        for action in CanvasActions(self).actions.values():
            self.addAction(action)

    def get_center_offset(self) -> tuple[int, int]:
        canvas = super().size()
        image = self.pixmap

        scale = self.get_scale()
        offset_x = (canvas.width() - image.width() * scale) / 2
        offset_y = (canvas.height() - image.height() * scale) / 2

        return int(offset_x), int(offset_y)

    def get_scale(self) -> float:
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

    def set_hovered_annotation(self, mouse_position: tuple[int, int]) -> None:
        annotations = self.get_visible_annotations()
        self.hovered_anno = None

        edge_width = round(8 / self.get_scale())
        edge_width = max(edge_width, 4)

        for annotation in annotations[::-1]:  # Prioritize newer annos
            hovered_type = annotation.get_hovered(mouse_position, edge_width)
            annotation.hovered = HoverType.NONE

            if hovered_type != HoverType.NONE and self.hovered_anno is None:
                annotation.hovered = hovered_type
                self.hovered_anno = annotation

    def set_selected_annotation(self, annotation: Annotation) -> None:
        for anno in self.annotations:
            anno.selected = False

        self.selected_annos = []
        self.add_selected_annotation(annotation)

    def add_selected_annotation(self, annotation: Annotation) -> None:
        if not annotation or annotation in self.selected_annos:
            return

        self.selected_annos.append(annotation)
        annotation.selected = True

    def hide_annotations(self) -> None:
        should_hide = not any(anno.hidden for anno in self.selected_annos)

        for anno in self.selected_annos:
            anno.hidden = should_hide

        self.update()

    def create_annotation(self) -> None:
        pass

    def move_annotation(self,
                        annotation: Annotation,
                        delta: tuple[int, int]
                        ) -> None:
        x_min, y_min, x_max, y_max = annotation.position
        delta_x, delta_y = delta

        hover_type = annotation.hovered

        right_border, left_border = self.pixmap.width(), 0
        bottom_border, top_border = self.pixmap.height(), 0

        if hover_type not in (HoverType.TOP, HoverType.BOTTOM):
            can_move_left = left_border <= x_min + delta_x <= right_border
            can_move_right = left_border <= x_max + delta_x <= right_border

            if hover_type & HoverType.LEFT and can_move_left:
                x_min += delta_x

            elif (hover_type & HoverType.RIGHT) and can_move_right:
                x_max += delta_x

            elif can_move_left and can_move_right:
                x_min += delta_x
                x_max += delta_x

        if hover_type not in (HoverType.LEFT, HoverType.RIGHT):
            can_move_top = top_border < y_min + delta_y < bottom_border
            can_move_bottom = top_border < y_max + delta_y < bottom_border

            if (hover_type & HoverType.TOP) and can_move_top:
                y_min += delta_y

            elif (hover_type & HoverType.BOTTOM) and can_move_bottom:
                y_max += delta_y

            elif can_move_top and can_move_bottom:
                y_min += delta_y
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

    def move_annotation_arrow(self, pressed_keys: set[int]) -> None:
        if not self.selected_annos:
            return

        delta_x, delta_y = 0, 0

        if Qt.Key.Key_Up in pressed_keys:
            delta_y -= 1
        if Qt.Key.Key_Down in pressed_keys:
            delta_y += 1
        if Qt.Key.Key_Left in pressed_keys:
            delta_x -= 1
        if Qt.Key.Key_Right in pressed_keys:
            delta_x += 1

        selected_anno = self.selected_annos[-1]
        self.set_selected_annotation(selected_anno)

        self.move_annotation(selected_anno, (delta_x, delta_y))
        self.update()

    def rename_annotations(self) -> None:
        pass

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

    def delete_annotations(self) -> None:
        self.annotations = list(filter(
            lambda anno: not anno.selected, self.annotations))

        self.update()

    def set_cursor_icon(self, event: QMouseEvent) -> None:
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

    def on_mouse_press(self, cursor_position: tuple[int, int]) -> None:
        self.set_hovered_annotation(cursor_position)

    def on_mouse_left_press(self, event: QMouseEvent) -> None:
        if Qt.KeyboardModifier.ControlModifier & event.modifiers():
            self.add_selected_annotation(self.hovered_anno)
        else:
            self.set_selected_annotation(self.hovered_anno)

    def on_mouse_right_press(self, event: QMouseEvent) -> None:
        if self.hovered_anno:
            self.set_selected_annotation(self.hovered_anno)
            context_menu = AnnotationContextMenu(self)

        else:
            context_menu = CanvasContextMenu(self)

        context_menu.exec(event.globalPosition().toPoint())

    def on_mouse_left_drag(self, cursor_shift: tuple[int, int]) -> None:
        if not self.hovered_anno:
            return

        self.move_annotation(self.hovered_anno, cursor_shift)

    def on_mouse_hover(self, cursor_position: tuple[int, int]) -> None:
        self.set_hovered_annotation(cursor_position)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.keyboard_handler.keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.keyboard_handler.keyReleaseEvent(event)

    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHints(__antialiasing__ | __pixmap_transform__)

        painter.translate(QPoint(*self.get_center_offset()))
        painter.scale(*[self.get_scale()] * 2)

        painter.drawPixmap(0, 0, self.pixmap)

        for annotation in self.get_visible_annotations():
            self.drawer.draw_annotation(self, painter, annotation)
