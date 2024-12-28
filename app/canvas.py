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
    QResizeEvent,
    QPaintEvent
)
from PyQt6.QtWidgets import QWidget

from app.actions import CanvasActions
from app.drawing import Drawer
from app.enums.annotation import HoverType, SelectionType
from app.enums.canvas import AnnotatingState
from app.handlers.actions import (
    ActionHandler,
    ActionCreate,
    ActionDelete,
    ActionMove,
    ActionRename,
    ActionMoveKeypoint,
    ActionDeleteKeypoints
)
from app.handlers.keyboard import KeyboardHandler
from app.handlers.mouse import MouseHandler
from app.handlers.zoom import ZoomHandler
from app.widgets.combo_box import ComboBox
from app.widgets.context_menu import AnnotationContextMenu, CanvasContextMenu
from app.objects import Annotation, Keypoint
from app.utils import clip_value

if TYPE_CHECKING:
    from annotator import MainWindow

__antialiasing__ = QPainter.RenderHint.Antialiasing
__pixmap_transform__ = QPainter.RenderHint.SmoothPixmapTransform


class Canvas(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__()
        self.parent = parent

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
        self.selected_keypoints = []

        self.hovered_anno = None
        self.hovered_keypoint = None

        self.mouse_handler = MouseHandler(self)
        self.setMouseTracking(True)

        self.keyboard_handler = KeyboardHandler(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.zoom_handler = ZoomHandler(self)

        self.action_handler = ActionHandler(self, self.image_name)
        self.anno_pos_before_move = None
        self.keypoint_pos_before_move = None

        for action in CanvasActions(self).actions.values():
            self.addAction(action)

        self.pin_annotation_list = False

    @property
    def labels(self) -> list[dict]:
        return self.parent.label_map_controller.labels

    @property
    def label_names(self) -> list[str]:
        return [label['name'] for label in self.labels]

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
        if self.annotating_state not in (AnnotatingState.MOVING_ANNO,
                                         AnnotatingState.MOVING_KEYPOINT):
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

        if self.hovered_keypoint is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
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

        image = QImageReader(image_path).read()
        self.pixmap = QPixmap.fromImage(image)

        self.image_name = os.path.basename(image_path)
        self.action_handler.image_name = self.image_name

        self.unsaved_changes = True
        self.update()

    def load_annotations(self, annotations: list[Annotation]) -> None:
        self.annotations = annotations
        self.update()

    def get_visible_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if not anno.hidden]

    def get_hidden_annotations(self) -> list[Annotation]:
        return [anno for anno in self.annotations if anno.hidden]

    def set_annotating_state(self, state: AnnotatingState) -> None:
        previous_state = self.annotating_state

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

        elif state == AnnotatingState.MOVING_ANNO:
            self.annotating_state = AnnotatingState.MOVING_ANNO

            if self.anno_pos_before_move is None:
                anno = self.selected_annos[-1]

                self.anno_pos_before_move = {
                    'annotation': anno.position,
                    'keypoints': None
                }

                if anno.has_keypoints:
                    self.anno_pos_before_move['keypoints'] = \
                        [keypoint.position.copy() for keypoint in anno.keypoints]

        elif state == AnnotatingState.MOVING_KEYPOINT:
            self.annotating_state = AnnotatingState.MOVING_KEYPOINT

            if self.keypoint_pos_before_move is None:
                self.keypoint_pos_before_move = self.selected_keypoints[-1].position

        # To prevent spam, register resize actions only when done resizing
        if (previous_state == AnnotatingState.MOVING_ANNO
                and state != AnnotatingState.MOVING_ANNO
                and self.selected_annos):
            anno = self.selected_annos[-1]

            position_to = {
                    'annotation': anno.position,
                    'keypoints': None
                }

            if anno.has_keypoints:
                position_to['keypoints'] = \
                    [keypoint.position for keypoint in anno.keypoints]

            action = ActionMove(self,
                                self.anno_pos_before_move,
                                position_to,
                                anno.label_name)

            self.action_handler.register_action(action)
            self.anno_pos_before_move = None

        if (previous_state == AnnotatingState.MOVING_KEYPOINT
                and state != AnnotatingState.MOVING_KEYPOINT
                and self.selected_keypoints):
            selected_keypoint = self.selected_keypoints[-1]
            kpt_idx = selected_keypoint.parent.keypoints.index(selected_keypoint)

            action = ActionMoveKeypoint(self,
                                        kpt_idx,
                                        self.keypoint_pos_before_move,
                                        selected_keypoint.position,
                                        selected_keypoint.parent.position,
                                        selected_keypoint.parent.label_name)

            self.action_handler.register_action(action)
            self.keypoint_pos_before_move = None

        self.update()

    def set_hovered_annotation(self) -> None:
        annotations = self.get_visible_annotations()

        self.hovered_anno = None
        self.hovered_keypoint = None

        for annotation in annotations:
            annotation.hovered = HoverType.NONE

            if not annotation.has_keypoints:
                continue

            for keypoint in annotation.keypoints:
                keypoint.hovered = False

        if self.annotating_state != AnnotatingState.IDLE:
            return

        mouse_position = self.mouse_handler.cursor_position
        edge_width = round(8 / self.get_scale())
        edge_width = max(edge_width, 4)

        for annotation in annotations[::-1]:  # Prioritize newer annos
            hovered_keypoint = annotation.get_hovered_keypoint(mouse_position, edge_width)

            if hovered_keypoint:
                annotation.hovered_keypoint = hovered_keypoint
                self.hovered_keypoint = hovered_keypoint
                hovered_keypoint.hovered = True
                return

            annotation.hovered_keypoint = None

        for annotation in annotations[::-1]:
            hovered_type = annotation.get_hovered(mouse_position, edge_width)

            if hovered_type != HoverType.NONE:
                annotation.hovered = hovered_type
                self.hovered_anno = annotation
                return

    def set_selected_annotation(self, annotation: Annotation | None) -> None:
        for anno in self.annotations:
            anno.selected = SelectionType.UNSELECTED

        self.selected_annos = []
        self.add_selected_annotation(annotation)

    def add_selected_annotation(self, annotation: Annotation | None) -> None:
        if not annotation or annotation in self.selected_annos:
            return

        self.selected_annos.append(annotation)
        annotation.selected = SelectionType.SELECTED
        annotation.hidden = False

    def select_next_annotation(self) -> None:
        if not self.annotations:
            return

        selected_idx = -1  # Newest annotation

        if len(self.selected_annos) > 1:
            selected_idx = self.annotations.index(self.selected_annos[-1])
        elif len(self.selected_annos) == 1:
            selected_idx = self.annotations.index(self.selected_annos[0]) - 1

        selected_idx %= len(self.annotations)

        self.set_selected_annotation(self.annotations[selected_idx])
        self.update()

    def select_all(self) -> None:
        if self.selected_keypoints:
            visited_annotations = []
            should_select = False

            for keypoint in self.selected_keypoints.copy():
                annotation = keypoint.parent

                if annotation in visited_annotations:
                    continue

                for kpt in keypoint.parent.keypoints:
                    if not kpt.selected:
                        should_select = True

                visited_annotations.append(annotation)

            if should_select:
                for annotation in visited_annotations:
                    for kpt in annotation.keypoints:
                        self.add_selected_keypoint(kpt)

            else:
                self.set_selected_keypoint(None)

            self.update()
            return

        should_select = len(self.selected_annos) != len(self.annotations)

        for annotation in self.annotations:
            if should_select:
                self.add_selected_annotation(annotation)
            else:
                self.unselect_annotation(annotation)

        self.update()

    def unselect_annotation(self, annotation: Annotation) -> None:
        annotation.selected = SelectionType.UNSELECTED

        if annotation in self.selected_annos:
            self.selected_annos.remove(annotation)

        self.update()

    def unselect_all(self) -> None:
        for annotation in self.selected_annos:
            self.unselect_annotation(annotation)

        self.update()

    def set_selected_keypoint(self, keypoint: Keypoint | None) -> None:
        for anno in self.annotations:

            if not anno.has_keypoints:
                continue

            for kpt in anno.keypoints:
                kpt.selected = False

        self.selected_keypoints = []
        self.add_selected_keypoint(keypoint)

    def add_selected_keypoint(self, keypoint: Keypoint | None) -> None:
        if not keypoint or keypoint in self.selected_keypoints:
            return

        self.selected_keypoints.append(keypoint)
        keypoint.selected = True

    def unselect_keypoint(self, keypoint: Keypoint) -> None:
        keypoint.selected = False

        if keypoint in self.selected_keypoints:
            self.selected_keypoints.remove(keypoint)

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

            combo_box = ComboBox(self, self.label_names)
            combo_box.exec(QPoint(x_pos - 35, y_pos - 20))

            label_name = combo_box.selected_value
            if not label_name:
                return

        self.previous_label = label_name

        position = [x_min, y_min, x_max, y_max]
        annotation = Annotation(position, label_name)

        action = ActionCreate(self, [(position, label_name, annotation.keypoints)])
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

                if annotation.selected == SelectionType.SELECTED \
                        and annotation.has_keypoints:
                    x_positions = [kpt.pos_x for kpt in annotation.keypoints if kpt.visible]
                    min_x, max_x = min(x_positions), max(x_positions)

                    if min_x + delta_x >= left_border and max_x + delta_x <= right_border:
                        for keypoint in annotation.keypoints:
                            keypoint.position[0] += delta_x

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

                if annotation.selected == SelectionType.SELECTED \
                        and annotation.has_keypoints:
                    y_positions = [kpt.pos_y for kpt in annotation.keypoints if
                                   kpt.visible]
                    min_y, max_y = min(y_positions), max(y_positions)

                    if min_y + delta_y >= top_border and max_y + delta_y <= bottom_border:
                        for keypoint in annotation.keypoints:
                            keypoint.position[1] += delta_y

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

    def move_arrow(self, pressed_keys: set[int]) -> None:
        if self.selected_annos:
            self.move_annotation_arrow(pressed_keys)

        elif self.selected_keypoints:
            self.move_keypoint_arrow(pressed_keys)

    def move_annotation_arrow(self, pressed_keys: set[int]) -> None:
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

        self.set_annotating_state(AnnotatingState.MOVING_ANNO)
        self.move_annotation(selected_anno, (delta_x, delta_y))

        self.unsaved_changes = True
        self.update()

    def move_keypoint(self,
                      keypoint: Keypoint,
                      delta: tuple[int, int]
                      ) -> None:
        pos_x, pos_y = keypoint.position
        delta_x, delta_y = delta

        pos_x = clip_value(pos_x + delta_x, 0, self.pixmap.width())
        pos_y = clip_value(pos_y + delta_y, 0, self.pixmap.height())

        keypoint.position = [pos_x, pos_y]
        self.unsaved_changes = True

    def move_keypoint_arrow(self, pressed_keys: set[int]) -> None:
        delta_x, delta_y = 0, 0

        if Qt.Key.Key_Up in pressed_keys:
            delta_y -= 1
        if Qt.Key.Key_Down in pressed_keys:
            delta_y += 1
        if Qt.Key.Key_Left in pressed_keys:
            delta_x -= 1
        if Qt.Key.Key_Right in pressed_keys:
            delta_x += 1

        selected_keypoint = self.selected_keypoints[-1]
        self.set_selected_keypoint(selected_keypoint)

        self.set_annotating_state(AnnotatingState.MOVING_KEYPOINT)
        self.move_keypoint(selected_keypoint, (delta_x, delta_y))

        self.unsaved_changes = True
        self.update()

    def rename_annotations(self) -> None:
        if not self.selected_annos:
            return

        cursor_position = self.mouse_handler.global_position
        x_pos, y_pos = cursor_position.x(), cursor_position.y()

        label_options = self.label_names

        # Narrow down the options to not allow renaming to a category
        # with a different keypoint structure
        label_map = self.parent.label_map_controller
        for annotation in self.selected_annos:
            if not annotation.has_keypoints:
                continue

            label_options = [option for option in label_options
                             if label_map.get_keypoint_info(option) ==
                             label_map.get_keypoint_info(annotation.label_name)]

        combo_box = ComboBox(self, label_options)
        combo_box.exec(QPoint(x_pos, y_pos + 20))

        label_name = combo_box.selected_value
        if not label_name:
            return

        renamed_annotations = []

        for annotation in self.selected_annos:
            renamed_annotations.append(
                (annotation.position, annotation.label_name, label_name))

            annotation.label_name = label_name

        action = ActionRename(self, renamed_annotations)
        self.action_handler.register_action(action)

        self.unsaved_changes = True
        self.update()

    def copy_annotations(self) -> None:
        all_annotations = self.annotations[::-1]

        selected = [anno for anno in all_annotations if anno.selected]
        to_copy = selected or all_annotations

        self.clipboard = copy.deepcopy(to_copy)

        for anno in self.clipboard:
            if anno.selected == SelectionType.BOX_ONLY:
                anno.keypoints = None

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
            annotation.selected = SelectionType.SELECTED
            annotation.hidden = False

            anno_info = annotation.position, annotation.label_name, annotation.keypoints
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
        deleted_keypoints = []

        for keypoint in self.selected_keypoints.copy():
            self.unselect_keypoint(keypoint)
            keypoint.visible = False

            anno = keypoint.parent
            anno_pos = anno.position
            label_name = anno.label_name
            kpt_idx = anno.keypoints.index(keypoint)

            deleted_keypoints.append((keypoint.position, kpt_idx, (anno_pos, label_name)))

        if deleted_keypoints:
            action = ActionDeleteKeypoints(self, deleted_keypoints)
            self.action_handler.register_action(action)

        filtered_annos = []
        deleted_annos = []

        for anno in self.annotations:
            if anno.selected:
                deleted_anno = anno.position, anno.label_name, anno.keypoints
                deleted_annos.append(deleted_anno)

            else:
                filtered_annos.append(anno)

        self.annotations = filtered_annos
        self.selected_annos = [anno for anno in self.selected_annos
                               if anno in filtered_annos]

        if deleted_annos:
            action = ActionDelete(self, deleted_annos)
            self.action_handler.register_action(action)

        self.unsaved_changes = True

        self.parent.annotation_list.redraw_widgets()
        self.update()

    def on_annotation_left_release(self, event: QMouseEvent) -> None:
        if self.annotating_state == AnnotatingState.MOVING_ANNO:
            return

        ctrl_pressed = bool(Qt.KeyboardModifier.ControlModifier & event.modifiers())
        selection_type = self.hovered_anno.selected

        if not ctrl_pressed:
            self.set_selected_annotation(self.hovered_anno)

        match ctrl_pressed, selection_type:
            case False, SelectionType.UNSELECTED:
                self.hovered_anno.selected = SelectionType.FRESHLY_SELECTED

            case False, SelectionType.FRESHLY_SELECTED:
                if self.hovered_anno.has_keypoints:
                    self.hovered_anno.selected = SelectionType.BOX_ONLY

            case False, SelectionType.SELECTED:
                if self.hovered_anno.has_keypoints:
                    self.hovered_anno.selected = SelectionType.BOX_ONLY

            case False, SelectionType.BOX_ONLY:
                self.hovered_anno.selected = SelectionType.SELECTED

            case True, SelectionType.UNSELECTED:
                self.add_selected_annotation(self.hovered_anno)
                self.hovered_anno.selected = SelectionType.FRESHLY_SELECTED

            case True, SelectionType.FRESHLY_SELECTED:
                if self.hovered_anno.has_keypoints:
                    self.hovered_anno.selected = SelectionType.BOX_ONLY
                else:
                    self.unselect_annotation(self.hovered_anno)

            case True, SelectionType.SELECTED:
                if self.hovered_anno.has_keypoints:
                    self.hovered_anno.selected = SelectionType.BOX_ONLY
                else:
                    self.unselect_annotation(self.hovered_anno)

            case True, SelectionType.BOX_ONLY:
                self.unselect_annotation(self.hovered_anno)

        self.update()

    def on_keypoint_left_press(self, event: QMouseEvent) -> None:
        if Qt.KeyboardModifier.ControlModifier & event.modifiers():
            if self.hovered_keypoint in self.selected_keypoints:
                self.unselect_keypoint(self.hovered_keypoint)

            else:
                self.add_selected_keypoint(self.hovered_keypoint)

        else:
            self.set_selected_keypoint(self.hovered_keypoint)

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
            self.set_annotating_state(AnnotatingState.IDLE)

            if not self.hovered_anno:
                self.set_selected_annotation(None)

            if self.hovered_keypoint:
                self.on_keypoint_left_press(event)
            else:
                self.set_selected_keypoint(None)

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
        if self.hovered_anno:
            box_only = self.hovered_anno.selected == SelectionType.BOX_ONLY

            self.set_selected_annotation(self.hovered_anno)
            if box_only:
                self.hovered_anno.selected = SelectionType.BOX_ONLY

            self.set_annotating_state(AnnotatingState.MOVING_ANNO)
            self.move_annotation(self.hovered_anno, cursor_shift)

        elif self.hovered_keypoint:
            self.set_selected_keypoint(self.hovered_keypoint)
            self.set_annotating_state(AnnotatingState.MOVING_KEYPOINT)
            self.move_keypoint(self.hovered_keypoint, cursor_shift)

        self.update()

    def on_mouse_right_drag(self, cursor_shift: tuple[int, int]) -> None:
        drag_start_x, drag_start_y = self.mouse_handler.drag_start_pan
        shift_x, shift_y = cursor_shift

        self.zoom_handler.pan_x = drag_start_x + shift_x
        self.zoom_handler.pan_y = drag_start_y + shift_y

        self.zoom_handler.clip_pan_values()
        if self.zoom_handler.zoom_level > 1:
            self.zoom_handler.set_indicator()

        self.update()

    def on_mouse_double_click(self, event: QMouseEvent) -> None:
        if not self.hovered_anno:
            return

        if self.hovered_anno.selected == SelectionType.UNSELECTED:
            if Qt.KeyboardModifier.ControlModifier & event.modifiers():
                self.add_selected_annotation(self.hovered_anno)
            else:
                self.set_selected_annotation(self.hovered_anno)

        elif self.hovered_anno.selected == SelectionType.FRESHLY_SELECTED:
            if self.hovered_anno.has_keypoints:
                self.hovered_anno.selected = SelectionType.BOX_ONLY
            elif Qt.KeyboardModifier.ControlModifier & event.modifiers():
                self.unselect_annotation(self.hovered_anno)

        self.update()

    def on_mouse_hover(self) -> None:
        if self.annotating_state in (AnnotatingState.MOVING_ANNO,
                                     AnnotatingState.MOVING_KEYPOINT):
            self.set_annotating_state(AnnotatingState.IDLE)

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

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.mouse_handler.wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.keyboard_handler.keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.keyboard_handler.keyReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.zoom_handler.clip_pan_values()
        super().resizeEvent(event)

    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHints(__antialiasing__ | __pixmap_transform__)

        painter.translate(QPoint(*self.get_center_offset()))
        painter.scale(*[self.get_scale()] * 2)

        painter.drawPixmap(0, 0, self.pixmap)

        for annotation in self.annotations:
            keypoint_info = self.parent.label_map_controller.get_keypoint_info(annotation.label_name)
            skeleton, symmetry = keypoint_info or (None, None)

            self.drawer.draw_annotation(self, painter, annotation, skeleton, symmetry)

        cursor_position = self.mouse_handler.cursor_position

        if self.annotating_state == AnnotatingState.READY:
            if self._is_cursor_in_bounds():
                self.drawer.draw_crosshair(self, painter, cursor_position)

        elif self.annotating_state == AnnotatingState.DRAWING:
            self.drawer.draw_candidate_annotation(
                self, painter, self.anno_first_corner, cursor_position)

        if self.zoom_handler.draw_indicator:
            zoom_level = self.zoom_handler.zoom_level
            self.drawer.draw_zoom_indicator(self, painter, zoom_level)
