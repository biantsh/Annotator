import copy
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import (
    QImageReader,
    QPixmap,
    QPainter,
    QMouseEvent,
    QWheelEvent,
    QKeyEvent,
    QPaintEvent
)
from PyQt6.QtWidgets import QWidget

from app.actions import CanvasActions
from app.drawing import Drawer
from app.enums.annotation import AnnotatingState, HoverType
from app.handlers.actions import (
    ActionHandler,
    ActionCreate,
    ActionDelete,
    ActionResize,
    ActionRename
)
from app.handlers.keyboard import KeyboardHandler
from app.handlers.mouse import MouseHandler
from app.handlers.zoom import ZoomHandler
from app.widgets.combo_box import ComboBox
from app.widgets.context_menu import AnnotationContextMenu, CanvasContextMenu
from app.objects import Annotation
from app.utils import clip_value

if TYPE_CHECKING:
    from annotator import MainWindow

__antialiasing__ = QPainter.RenderHint.Antialiasing
__pixmap_transform__ = QPainter.RenderHint.SmoothPixmapTransform


class Canvas(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__()
        self.parent = parent

        self.labels = []
        self.clipboard = []

        self.quick_create = False
        self.previous_label = None

        self.unsaved_changes = False
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.save_progress)
        self.auto_save_timer.start(3000)

        self.image_name = None
        self.pixmap = QPixmap()
        self.drawer = Drawer()

        self.annotating_state = AnnotatingState.IDLE
        self.anno_first_corner = None

        self.annotations = []
        self.selected_annos = []
        self.hovered_anno = None

        self.mouse_handler = MouseHandler(self)
        self.setMouseTracking(True)

        self.keyboard_handler = KeyboardHandler(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.zoom_handler = ZoomHandler(self)

        self.action_handler = ActionHandler(self, self.image_name)
        self.anno_pos_before_resize = None

        for action in CanvasActions(self).actions.values():
            self.addAction(action)

        self.pin_annotation_list = False

    def _is_cursor_in_bounds(self) -> bool:
        x_pos, y_pos = self.mouse_handler.cursor_position

        pixmap_size = self.pixmap.size()
        width, height = pixmap_size.width(), pixmap_size.height()

        return 0 <= x_pos <= width and 0 <= y_pos <= height

    def get_center_offset(self) -> tuple[int, int]:
        canvas = self.size()
        image = self.pixmap

        scale = self.get_scale()
        offset_x = (canvas.width() - image.width() * scale) / 2
        offset_y = (canvas.height() - image.height() * scale) / 2

        offset_x += self.zoom_handler.pan_x
        offset_y += self.zoom_handler.pan_y

        return int(offset_x), int(offset_y)

    def get_scale(self) -> float:
        if self.pixmap.isNull():
            return 1.0

        canvas = super().size()
        image = self.pixmap

        canvas_aspect = canvas.width() / canvas.height()
        image_aspect = image.width() / image.height()

        scale = canvas.height() / image.height()

        if canvas_aspect < image_aspect:
            scale = canvas.width() / image.width()

        return scale * self.zoom_handler.zoom_level

    def reset(self) -> None:
        self.set_annotating_state(AnnotatingState.IDLE)
        self.set_selected_annotation(None)

        self.annotations = []
        self.pixmap = QPixmap()
        self.zoom_handler.reset()

        self.update()

    def save_progress(self) -> None:
        if not self.unsaved_changes:
            return

        self.unsaved_changes = False
        image_size = self.pixmap.width(), self.pixmap.height()

        self.parent.annotation_controller.save_annotations(
            self.image_name, image_size, self.annotations)

    def update(self) -> None:
        if self.annotating_state != AnnotatingState.RESIZING:
            self.set_hovered_annotation()

        self.update_cursor_icon()
        self.parent.annotation_list.update()

        super().update()

    def update_cursor_icon(self) -> None:
        if not self._is_cursor_in_bounds():
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self.annotating_state in (AnnotatingState.READY,
                                     AnnotatingState.DRAWING):
            self.setCursor(Qt.CursorShape.CrossCursor)
            return

        left_clicked = self.mouse_handler.left_clicked
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

    def load_image(self, image_path: str) -> None:
        self.reset()

        self.image_name = os.path.basename(image_path)
        image = QImageReader(image_path).read()
        self.pixmap = QPixmap.fromImage(image)

        self.action_handler.image_name = self.image_name
        self.update()

    def load_annotations(self, annotations: list[Annotation]) -> None:
        self.annotations = annotations
        self.update()

    def get_visible_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if not anno.hidden]

    def get_hidden_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if anno.hidden]

    def set_annotating_state(self, state: AnnotatingState) -> None:
        # To prevent spam, register ResizeAction only when done resizing
        if (self.annotating_state == AnnotatingState.RESIZING
                and state != AnnotatingState.RESIZING):
            if not self.selected_annos:
                return

            action = ActionResize(self,
                                  self.anno_pos_before_resize,
                                  self.selected_annos[-1].position,
                                  self.selected_annos[-1].label_name)

            self.action_handler.register_action(action)
            self.anno_pos_before_resize = None

        if state == AnnotatingState.IDLE:
            self.annotating_state = AnnotatingState.IDLE
            self.anno_first_corner = None

        elif state == AnnotatingState.READY:
            self.annotating_state = AnnotatingState.READY
            self.set_selected_annotation(None)
            self.set_hovered_annotation()

        elif state == AnnotatingState.DRAWING:
            self.annotating_state = AnnotatingState.DRAWING
            self.anno_first_corner = self.mouse_handler.cursor_position

        elif state == AnnotatingState.RESIZING:
            self.annotating_state = AnnotatingState.RESIZING

            if self.anno_pos_before_resize is None:
                self.anno_pos_before_resize = self.selected_annos[-1].position

        self.update()

    def set_hovered_annotation(self) -> None:
        annotations = self.get_visible_annotations()

        self.hovered_anno = None
        for annotation in annotations:
            annotation.hovered = HoverType.NONE

        if self.annotating_state != AnnotatingState.IDLE:
            return

        mouse_position = self.mouse_handler.cursor_position
        edge_width = round(8 / self.get_scale())
        edge_width = max(edge_width, 4)

        for annotation in annotations[::-1]:  # Prioritize newer annos
            hovered_type = annotation.get_hovered(mouse_position, edge_width)

            if hovered_type != HoverType.NONE:
                annotation.hovered = hovered_type
                self.hovered_anno = annotation

                return

    def set_selected_annotation(self, annotation: Annotation | None) -> None:
        for anno in self.annotations:
            anno.selected = False

        self.selected_annos = []
        self.add_selected_annotation(annotation)

    def add_selected_annotation(self, annotation: Annotation | None) -> None:
        if not annotation or annotation in self.selected_annos:
            return

        self.selected_annos.append(annotation)
        annotation.selected = True
        annotation.hidden = False

    def select_next_annotation(self) -> None:
        selected_idx = -1  # Newest annotation

        if len(self.selected_annos) > 1:
            selected_idx = self.annotations.index(self.selected_annos[-1])
        elif len(self.selected_annos) == 1:
            selected_idx = self.annotations.index(self.selected_annos[0]) - 1

        selected_idx %= len(self.annotations)

        self.set_selected_annotation(self.annotations[selected_idx])
        self.update()

    def select_all(self) -> None:
        should_select = len(self.selected_annos) != len(self.annotations)

        for annotation in self.annotations:
            if should_select:
                self.add_selected_annotation(annotation)
            else:
                self.unselect_annotation(annotation)

        self.update()

    def unselect_annotation(self, annotation: Annotation) -> None:
        annotation.selected = False

        if annotation in self.selected_annos:
            self.selected_annos.remove(annotation)

        self.update()

    def unselect_all(self) -> None:
        for annotation in self.selected_annos:
            self.unselect_annotation(annotation)

        self.update()

    def hide_annotations(self) -> None:
        should_hide = not any(anno.hidden for anno in self.selected_annos)

        for anno in self.selected_annos:
            anno.hidden = should_hide

        self.update()

    def create_annotation(self, label_name: str = None) -> None:
        x_min, y_min = self.anno_first_corner
        x_max, y_max = self.mouse_handler.cursor_position

        left_border, right_border = 0, self.pixmap.width()
        top_border, bottom_border = 0, self.pixmap.height()

        x_min = clip_value(x_min, left_border, right_border)
        x_max = clip_value(x_max, left_border, right_border)
        y_min = clip_value(y_min, top_border, bottom_border)
        y_max = clip_value(y_max, top_border, bottom_border)

        x_min, x_max = sorted((x_min, x_max))
        y_min, y_max = sorted((y_min, y_max))

        if not label_name:
            cursor_position = self.mouse_handler.global_position
            x_pos, y_pos = cursor_position.x(), cursor_position.y()

            combo_box = ComboBox(self, self.labels)
            combo_box.exec(QPoint(x_pos - 35, y_pos - 20))

            label_name = combo_box.selected_value
            if not label_name:
                return

        self.previous_label = label_name

        position = [x_min, y_min, x_max, y_max]
        category_id = self.labels.index(label_name) + 1
        annotation = Annotation(position, category_id, label_name)

        action = ActionCreate(self, [(position, label_name)])
        self.action_handler.register_action(action)

        self.annotations.append(annotation)
        self.set_selected_annotation(annotation)
        self.unsaved_changes = True

        self.parent.annotation_list.redraw_widgets()

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
            can_move_top = top_border <= y_min + delta_y <= bottom_border
            can_move_bottom = top_border <= y_max + delta_y <= bottom_border

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

        annotation.position = [x_min, y_min, x_max, y_max]
        self.unsaved_changes = True

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

        self.set_annotating_state(AnnotatingState.RESIZING)
        self.move_annotation(selected_anno, (delta_x, delta_y))

        self.unsaved_changes = True
        self.update()

    def rename_annotations(self) -> None:
        if not self.selected_annos:
            return

        cursor_position = self.mouse_handler.global_position
        x_pos, y_pos = cursor_position.x(), cursor_position.y()

        combo_box = ComboBox(self, self.labels)
        combo_box.exec(QPoint(x_pos, y_pos + 20))

        label_name = combo_box.selected_value
        if not label_name:
            return

        renamed_annotations = []

        for annotation in self.selected_annos:
            renamed_annotations.append(
                (annotation.position, annotation.label_name, label_name))

            annotation.label_name = label_name
            annotation.category_id = self.labels.index(label_name) + 1

        action = ActionRename(self, renamed_annotations)
        self.action_handler.register_action(action)

        self.unsaved_changes = True
        self.update()

    def copy_annotations(self) -> None:
        all_annotations = self.annotations[::-1]

        selected = [anno for anno in all_annotations if anno.selected]
        to_copy = selected or all_annotations

        self.clipboard = copy.deepcopy(to_copy)

    def paste_annotations(self, replace_existing: bool) -> None:
        pasted_annotations = copy.deepcopy(self.clipboard)
        if not pasted_annotations:
            return

        if replace_existing:  # Delete existing annotations
            for annotation in self.annotations:
                self.add_selected_annotation(annotation)

            self.delete_selected()

        pasted_anno_info = []
        self.set_selected_annotation(None)

        for annotation in pasted_annotations[::-1]:
            if annotation in self.annotations:
                continue

            annotation.hovered = HoverType.NONE
            annotation.selected = True
            annotation.hidden = False

            anno_info = annotation.position, annotation.label_name
            pasted_anno_info.append(anno_info)

            self.annotations.append(annotation)
            self.add_selected_annotation(annotation)

        self.set_annotating_state(AnnotatingState.IDLE)

        if pasted_anno_info:
            action = ActionCreate(self, pasted_anno_info)
            self.action_handler.register_action(action)

            self.parent.annotation_list.redraw_widgets()
            self.unsaved_changes = True

    def delete_selected(self) -> None:
        filtered_annos = []
        deleted_annos = []

        for anno in self.annotations:
            if anno.selected:
                deleted_anno = anno.position, anno.label_name
                deleted_annos.append(deleted_anno)

            else:
                filtered_annos.append(anno)

        action = ActionDelete(self, deleted_annos)
        self.action_handler.register_action(action)

        self.annotations = filtered_annos
        self.unsaved_changes = True

        self.parent.annotation_list.redraw_widgets()
        self.update()

    def on_annotation_left_press(self, event: QMouseEvent) -> None:
        if Qt.KeyboardModifier.ControlModifier & event.modifiers():
            if self.hovered_anno in self.selected_annos:
                self.unselect_annotation(self.hovered_anno)

            else:
                self.add_selected_annotation(self.hovered_anno)
        else:
            self.set_selected_annotation(self.hovered_anno)

    def on_mouse_left_press(self, event: QMouseEvent) -> None:
        if self.annotating_state == AnnotatingState.READY:
            self.set_annotating_state(AnnotatingState.DRAWING)

        elif self.annotating_state == AnnotatingState.DRAWING:
            if self.quick_create:
                self.create_annotation(self.previous_label)
                self.quick_create = False
            else:
                self.create_annotation()

            self.set_annotating_state(AnnotatingState.IDLE)

        else:
            self.on_annotation_left_press(event)

        self.update()

    def on_mouse_right_press(self, event: QMouseEvent) -> None:
        self.set_annotating_state(AnnotatingState.IDLE)

        if self.hovered_anno:
            self.set_selected_annotation(self.hovered_anno)
            context_menu = AnnotationContextMenu(self)

        else:
            if self.pin_annotation_list:
                return

            context_menu = CanvasContextMenu(self)

        context_menu.exec(event.globalPosition().toPoint())
        self.update()

    def on_mouse_left_drag(self, cursor_shift: tuple[int, int]) -> None:
        if not self.hovered_anno:
            return

        self.set_annotating_state(AnnotatingState.RESIZING)
        self.move_annotation(self.hovered_anno, cursor_shift)

        self.update()

    def on_mouse_hover(self) -> None:
        self.update()

    def on_mouse_middle_press(self, cursor_position: tuple[int, int]) -> None:
        if not self._is_cursor_in_bounds():
            return

        self.zoom_handler.toggle_zoom(cursor_position)
        self.update()

    def on_scroll_up(self, cursor_position: tuple[int, int]) -> None:
        if not self._is_cursor_in_bounds():
            return

        self.zoom_handler.zoom_in(cursor_position)
        self.update()

    def on_scroll_down(self, cursor_position: tuple[int, int]) -> None:
        if not self._is_cursor_in_bounds():
            return

        self.zoom_handler.zoom_out(cursor_position)
        self.update()

    def on_escape(self) -> None:
        self.set_annotating_state(AnnotatingState.IDLE)

        for annotation in self.annotations:
            self.unselect_annotation(annotation)
            annotation.highlighted = False

        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.mouse_handler.wheelEvent(event)

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

        for annotation in self.annotations:
            self.drawer.draw_annotation(self, painter, annotation)

        cursor_position = self.mouse_handler.cursor_position

        if self.annotating_state == AnnotatingState.READY:
            if self._is_cursor_in_bounds():
                self.drawer.draw_crosshair(self, painter, cursor_position)

        elif self.annotating_state == AnnotatingState.DRAWING:
            self.drawer.draw_candidate_annotation(
                self, painter, self.anno_first_corner, cursor_position)
