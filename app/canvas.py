import copy
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import (
    QImageReader,
    QPixmap,
    QMouseEvent,
    QWheelEvent,
    QKeyEvent,
    QResizeEvent,
    QPaintEvent
)
from PyQt6.QtWidgets import QWidget

from app.actions import CanvasActions
from app.controllers.label_map_controller import LabelMapController
from app.enums.annotation import HoverType, SelectionType
from app.enums.canvas import AnnotatingState
from app.handlers.actions import (
    ActionHandler,
    ActionCreate,
    ActionDelete,
    ActionMove,
    ActionRename,
    ActionAddBbox,
    ActionDeleteBbox,
    ActionCreateKeypoints,
    ActionDeleteKeypoints,
    ActionMoveKeypoint,
    ActionFlipKeypoints
)
from app.handlers.annotator import KeypointAnnotator
from app.handlers.keyboard import KeyboardHandler
from app.handlers.mouse import MouseHandler
from app.handlers.painter import CanvasPainter
from app.handlers.zoom import ZoomHandler
from app.widgets.combo_box import ComboBox
from app.widgets.context_menu import AnnotationContextMenu, CanvasContextMenu
from app.objects import Annotation, Keypoint
from app.utils import clip_value

if TYPE_CHECKING:
    from annotator import MainWindow


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

        self.keypoint_annotator = KeypointAnnotator(self)
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

        self.action_handler = ActionHandler(self, self.image_name)
        self.zoom_handler = ZoomHandler(self)

        self.pos_start_anno = None
        self.pos_start_kpt = None

        for action in CanvasActions(self).actions.values():
            self.addAction(action)

    @property
    def label_map(self) -> LabelMapController:
        return self.parent.label_map_controller

    @property
    def label_names(self) -> list[str]:
        return [label['name'] for label in self.label_map.labels]

    def on_next(self) -> None:
        if self.keypoint_annotator.active:
            self.keypoint_annotator.next_label()

        else:
            self.parent.next_image()

    def on_prev(self) -> None:
        if self.keypoint_annotator.active:
            self.keypoint_annotator.prev_label()

        else:
            self.parent.prev_image()

    def update(self) -> None:
        self.update_cursor_icon()
        self.parent.annotation_list.update()

        super().update()

    def reset(self) -> None:
        self.annotations = []
        self.zoom_handler.reset()

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
        self.set_hovered_object()

        self.unselect_all()
        self.update()

    def save_progress(self) -> None:
        if not self.unsaved_changes:
            return

        self.unsaved_changes = False
        image_size = self.pixmap.width(), self.pixmap.height()

        self.parent.annotation_controller.save_annotations(
            self.image_name, image_size, self.annotations)

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

    def is_cursor_in_bounds(self) -> bool:
        x_pos, y_pos = self.mouse_handler.cursor_position

        pixmap_size = self.pixmap.size()
        width, height = pixmap_size.width(), pixmap_size.height()

        return 0 <= x_pos <= width and 0 <= y_pos <= height

    def update_cursor_icon(self) -> None:
        if not self.is_cursor_in_bounds():
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self.annotating_state in (AnnotatingState.READY,
                                     AnnotatingState.DRAWING_ANNO):
            self.setCursor(Qt.CursorShape.CrossCursor)
            return

        if self.keypoint_annotator.active or self.hovered_keypoint:
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

    def set_annotating_state(self, state: AnnotatingState) -> None:
        if state == AnnotatingState.DRAWING_KEYPOINTS:
            self.create_keypoints()

            if self.keypoint_annotator.active:
                self.annotating_state = AnnotatingState.DRAWING_KEYPOINTS

            return

        previous_state = self.annotating_state
        self.annotating_state = state

        if state == AnnotatingState.IDLE:
            self.anno_first_corner = None

        elif state == AnnotatingState.READY:
            self.set_selected_annotation(None)
            self.set_hovered_object()

        elif state == AnnotatingState.DRAWING_ANNO:
            self.anno_first_corner = self.mouse_handler.cursor_position

        elif state == AnnotatingState.MOVING_ANNO:
            anno = self.selected_annos[-1]

            self.pos_start_anno = self.pos_start_anno or {
                'annotation': anno.position or anno.implicit_bbox,
                'keypoints': [kpt.position.copy() for kpt in anno.keypoints]}

        elif state == AnnotatingState.MOVING_KEYPOINT:
            self.pos_start_kpt = self.pos_start_kpt \
                or self.selected_keypoints[-1].position

        if (previous_state == AnnotatingState.MOVING_ANNO
                and state != AnnotatingState.MOVING_ANNO):
            pos_start = self.pos_start_anno['annotation']
            pos_start_kpts = self.pos_start_anno['keypoints']
            self.pos_start_anno = None

            self.action_handler.register_action(ActionMove(
                self, self.selected_annos[-1], pos_start, pos_start_kpts))

        if (previous_state == AnnotatingState.MOVING_KEYPOINT
                and state != AnnotatingState.MOVING_KEYPOINT):
            pos_start = self.pos_start_kpt
            self.pos_start_kpt = None

            self.action_handler.register_action(ActionMoveKeypoint(
                self, self.selected_keypoints[-1], pos_start))

        self.update()

    def set_hovered_object(self) -> None:
        self.hovered_keypoint = None
        self.hovered_anno = None

        for anno in self.annotations:
            anno.hovered = HoverType.NONE

            for keypoint in anno.keypoints:
                keypoint.hovered = False

        if self.annotating_state != AnnotatingState.IDLE:
            return

        mouse_pos = self.mouse_handler.cursor_position

        for anno in self.annotations[::-1]:
            hovered_keypoint = anno.get_hovered_keypoint(mouse_pos)
            hovered_type = anno.get_hovered_type(mouse_pos)

            if hovered_keypoint and not anno.hidden:
                self.hovered_keypoint = hovered_keypoint
                hovered_keypoint.hovered = True
                return

            if hovered_type and not anno.hidden:
                self.hovered_anno = anno
                anno.hovered = hovered_type
                return

    def set_selected_annotation(self, annotation: Annotation | None) -> None:
        for anno in self.annotations:
            anno.selected = SelectionType.UNSELECTED

        self.selected_annos = []
        self.add_selected_annotation(annotation)

    def add_selected_annotation(self, annotation: Annotation | None) -> None:
        if not annotation or annotation in self.selected_annos:
            return

        self.set_selected_keypoint(None)

        self.selected_annos.append(annotation)
        annotation.selected = SelectionType.SELECTED
        annotation.hidden = False

    def unselect_annotation(self, annotation: Annotation) -> None:
        annotation.selected = SelectionType.UNSELECTED

        if annotation in self.selected_annos:
            self.selected_annos.remove(annotation)

    def set_selected_keypoint(self, keypoint: Keypoint | None) -> None:
        for anno in self.annotations:
            for kpt in anno.keypoints:
                kpt.selected = False

        self.selected_keypoints = []
        self.add_selected_keypoint(keypoint)

    def add_selected_keypoint(self, keypoint: Keypoint | None) -> None:
        if not keypoint or keypoint in self.selected_keypoints:
            return

        self.set_selected_annotation(None)

        self.selected_keypoints.append(keypoint)
        keypoint.selected = True

    def unselect_keypoint(self, keypoint: Keypoint) -> None:
        if keypoint not in self.selected_keypoints:
            return

        self.selected_keypoints.remove(keypoint)
        keypoint.selected = False

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
            visible_kpts = []

            for keypoint in self.selected_keypoints:
                for kpt in keypoint.parent.keypoints:
                    if kpt.visible:
                        visible_kpts.append(kpt)

            if all(kpt.selected for kpt in visible_kpts):
                self.set_selected_keypoint(None)

            else:
                for keypoint in visible_kpts:
                    self.add_selected_keypoint(keypoint)

        else:
            if all(anno.selected for anno in self.annotations):
                self.set_selected_annotation(None)

            else:
                for annotation in self.annotations:
                    self.add_selected_annotation(annotation)

        self.update()

    def unselect_all(self) -> None:
        self.set_selected_annotation(None)
        self.set_selected_keypoint(None)

    def create_annotation(self, label_name: str = None) -> None:
        x_min, y_min = self.anno_first_corner
        x_max, y_max = self.mouse_handler.cursor_position

        x_min = clip_value(x_min, 0, self.pixmap.width())
        x_max = clip_value(x_max, 0, self.pixmap.width())
        y_min = clip_value(y_min, 0, self.pixmap.height())
        y_max = clip_value(y_max, 0, self.pixmap.height())

        x_min, x_max = sorted([x_min, x_max])
        y_min, y_max = sorted([y_min, y_max])

        if not (label_name and self.label_map.contains(label_name)):
            cursor_position = self.mouse_handler.global_position
            x_pos, y_pos = cursor_position.x(), cursor_position.y()

            combo_box = ComboBox(self, self.label_names)
            combo_box.exec(QPoint(x_pos - 35, y_pos - 20))

            label_name = combo_box.selected_value
            if not label_name:
                return

        label_schema = self.label_map.get_label_schema(label_name)
        annotation = Annotation(label_schema, [x_min, y_min, x_max, y_max])

        self.action_handler.register_action(ActionCreate(self, [annotation]))
        self.previous_label = label_name

    def create_keypoints(self, label_name: str = None) -> None:
        if label_name:
            if not self.label_map.contains(label_name):
                return

            loaded_schema = self.label_map.get_label_schema(label_name)

            if not loaded_schema.kpt_names:
                return

            annotation = Annotation(loaded_schema)

        elif self.selected_annos or self.selected_keypoints:
            annotation = self.selected_annos[-1] if self.selected_annos \
                else self.selected_keypoints[-1].parent

            label_name = annotation.label_name

            if not annotation.label_schema.kpt_names:
                if not self.label_map.contains(label_name):
                    return

                loaded_schema = self.label_map.get_label_schema(label_name)
                if not loaded_schema.kpt_names:
                    return

                annotation.set_schema(loaded_schema)

        else:
            cursor_position = self.mouse_handler.global_position
            x_pos, y_pos = cursor_position.x(), cursor_position.y()

            options = [option for option in self.label_names
                       if self.label_map.get_label_schema(option).kpt_names]

            combo_box = ComboBox(self, options)
            combo_box.exec(QPoint(x_pos - 35, y_pos - 20))

            label_name = combo_box.selected_value
            if not label_name:
                return

            label_schema = self.label_map.get_label_schema(label_name)
            annotation = Annotation(label_schema)

        for action in self.actions():
            action.setEnabled(False)

        self.keypoint_annotator.begin(annotation)

    def rename_annotations(self) -> None:
        if not self.selected_annos:
            return

        label_options = self.label_names

        for anno in self.selected_annos:
            if not anno.has_keypoints:
                continue

            label_options = [
                option for option in label_options if anno.kpt_names
                == self.label_map.get_label_schema(option).kpt_names]

        cursor_position = self.mouse_handler.global_position
        pos_x, pos_y = cursor_position.x(), cursor_position.y()

        combo_box = ComboBox(self, label_options)
        combo_box.exec(QPoint(pos_x, pos_y + 20))

        label_name = combo_box.selected_value
        if not label_name:
            return

        label_schema = self.label_map.get_label_schema(label_name)
        self.action_handler.register_action(ActionRename(
            self, self.selected_annos, label_schema))

    def copy_annotations(self) -> None:
        to_copy = self.annotations[::-1]

        if self.selected_annos:
            to_copy = filter(lambda anno: anno.selected, to_copy)

        self.clipboard = [copy.copy(anno) for anno in to_copy]

    def paste_annotations(self, replace_existing: bool) -> None:
        existing_positions = [anno.position or anno.implicit_bbox
                              for anno in self.annotations]

        pasted_annos = [copy.copy(anno) for anno in self.clipboard[::-1]
                        if (anno.position or anno.implicit_bbox)
                        not in existing_positions]

        if not pasted_annos:
            return

        if replace_existing and self.annotations:
            action = ActionDelete(self, self.annotations)
            self.action_handler.register_action(action)

        action = ActionCreate(self, pasted_annos)
        self.action_handler.register_action(action)

    def hide_annotations(self) -> None:
        should_hide = not any(anno.hidden for anno in self.selected_annos)

        for anno in self.selected_annos:
            anno.hidden = should_hide

        self.update()

    def delete_annotations(self) -> None:
        if self.selected_keypoints:
            action = ActionDeleteKeypoints(self, self.selected_keypoints)
            self.action_handler.register_action(action)

        if self.selected_annos:
            to_delete_bbox = []
            to_delete = []

            for anno in self.selected_annos:
                if anno.selected == SelectionType.BOX_ONLY:
                    to_delete_bbox.append(anno)
                else:
                    to_delete.append(anno)

            if to_delete_bbox:
                action = ActionDeleteBbox(self, to_delete_bbox)
                self.action_handler.register_action(action)

            if to_delete:
                action = ActionDelete(self, to_delete)
                self.action_handler.register_action(action)

    def add_bboxes(self) -> None:
        annos = [anno for anno in self.selected_annos if not anno.has_bbox]

        if annos:
            action = ActionAddBbox(self, annos)
            self.action_handler.register_action(action)

    def move_annotation(self,
                        anno: Annotation,
                        delta: tuple[int, int]
                        ) -> None:
        x_min, y_min, x_max, y_max = anno.position or anno.implicit_bbox
        delta_x, delta_y = delta

        kpts_x, kpts_y = None, None
        edge_right, edge_bot = self.pixmap.width(), self.pixmap.height()

        if anno.has_keypoints and anno.selected != SelectionType.BOX_ONLY:
            kpts_x, kpts_y = zip(*[keypoint.position for keypoint in
                                   anno.keypoints if keypoint.visible])

        if anno.hovered not in (HoverType.TOP, HoverType.BOTTOM):
            can_move_left = 0 <= x_min + delta_x <= edge_right
            can_move_right = 0 <= x_max + delta_x <= edge_right

            if anno.hovered & HoverType.LEFT and can_move_left:
                x_min += delta_x

            elif anno.hovered & HoverType.RIGHT and can_move_right:
                x_max += delta_x

            elif can_move_left and can_move_right:
                x_min += delta_x
                x_max += delta_x

                if kpts_x and min(kpts_x) + delta_x >= 0 \
                        and max(kpts_x) + delta_x <= edge_right:
                    for keypoint in anno.keypoints:
                        keypoint.position[0] += delta_x

        if anno.hovered not in (HoverType.LEFT, HoverType.RIGHT):
            can_move_top = 0 <= y_min + delta_y <= edge_bot
            can_move_bot = 0 <= y_max + delta_y <= edge_bot

            if anno.hovered & HoverType.TOP and can_move_top:
                y_min += delta_y

            elif anno.hovered & HoverType.BOTTOM and can_move_bot:
                y_max += delta_y

            elif can_move_top and can_move_bot:
                y_min += delta_y
                y_max += delta_y

                if kpts_y and min(kpts_y) + delta_y >= 0 \
                        and max(kpts_y) + delta_y <= edge_bot:
                    for keypoint in anno.keypoints:
                        keypoint.position[1] += delta_y

        if anno.has_bbox:
            anno.position = [x_min, y_min, x_max, y_max]
        else:
            anno.fit_bbox_to_keypoints()

    def move_keypoint(self,
                      keypoint: Keypoint,
                      delta: tuple[int, int]
                      ) -> None:
        pos_x, pos_y = keypoint.position
        delta_x, delta_y = delta

        pos_x = clip_value(pos_x + delta_x, 0, self.pixmap.width())
        pos_y = clip_value(pos_y + delta_y, 0, self.pixmap.height())

        keypoint.position = [pos_x, pos_y]

    def move_annotation_arrow(self, delta: tuple[int, int]) -> None:
        selected_anno = self.selected_annos[-1]
        selection_type = selected_anno.selected

        if selection_type == SelectionType.NEWLY_SELECTED:
            selection_type = SelectionType.SELECTED

        self.set_selected_annotation(selected_anno)
        selected_anno.selected = selection_type

        self.set_annotating_state(AnnotatingState.MOVING_ANNO)
        self.move_annotation(selected_anno, delta)

    def move_keypoint_arrow(self, delta: tuple[int, int]) -> None:
        selected_keypoint = self.selected_keypoints[-1]
        self.set_selected_keypoint(selected_keypoint)

        self.set_annotating_state(AnnotatingState.MOVING_KEYPOINT)
        self.move_keypoint(selected_keypoint, delta)

    def flip_keypoints(self) -> None:
        action = ActionFlipKeypoints(self, self.selected_annos[-1])
        self.action_handler.register_action(action)

    def on_keypoints_created(self) -> None:
        for action in self.actions():
            action.setEnabled(True)

        created_keypoints = self.keypoint_annotator.created_keypoints
        annotation = self.keypoint_annotator.annotation

        if not created_keypoints:
            self.unselect_all()
            return

        if annotation in self.annotations:
            action = ActionCreateKeypoints(self, created_keypoints)
        else:
            annotation.fit_bbox_to_keypoints()
            action = ActionCreate(self, [annotation])

        self.action_handler.register_action(action)
        self.previous_label = annotation.label_name

    def on_arrow_press(self, pressed_keys: set[int]) -> None:
        delta_x, delta_y = 0, 0

        if Qt.Key.Key_Up in pressed_keys:
            delta_y -= 1
        if Qt.Key.Key_Down in pressed_keys:
            delta_y += 1
        if Qt.Key.Key_Left in pressed_keys:
            delta_x -= 1
        if Qt.Key.Key_Right in pressed_keys:
            delta_x += 1

        if self.selected_annos:
            self.move_annotation_arrow((delta_x, delta_y))

        elif self.selected_keypoints:
            self.move_keypoint_arrow((delta_x, delta_y))

    def on_annotation_left_press(self, event: QMouseEvent) -> None:
        if self.annotating_state == AnnotatingState.MOVING_ANNO:
            return

        annotation = self.hovered_anno
        selection_type = annotation.selected
        ctrl_pressed = Qt.KeyboardModifier.ControlModifier & event.modifiers()

        if not ctrl_pressed:
            self.set_selected_annotation(annotation)

        match bool(ctrl_pressed), selection_type:
            case False, SelectionType.UNSELECTED:
                annotation.selected = SelectionType.NEWLY_SELECTED

            case False, SelectionType.SELECTED | SelectionType.NEWLY_SELECTED:
                if annotation.has_bbox and annotation.has_keypoints:
                    annotation.selected = SelectionType.BOX_ONLY

            case False, SelectionType.BOX_ONLY:
                annotation.selected = SelectionType.SELECTED

            case True, SelectionType.UNSELECTED:
                self.add_selected_annotation(annotation)
                annotation.selected = SelectionType.NEWLY_SELECTED

            case True, SelectionType.SELECTED | SelectionType.NEWLY_SELECTED:
                if annotation.has_bbox and annotation.has_keypoints:
                    annotation.selected = SelectionType.BOX_ONLY
                else:
                    self.unselect_annotation(annotation)

            case True, SelectionType.BOX_ONLY:
                self.unselect_annotation(annotation)

        self.update()

    def on_keypoint_left_press(self,
                               keypoint: Keypoint,
                               event: QMouseEvent
                               ) -> None:
        if Qt.KeyboardModifier.ControlModifier & event.modifiers():
            if keypoint in self.selected_keypoints:
                self.unselect_keypoint(keypoint)

            else:
                self.add_selected_keypoint(keypoint)

        else:
            self.set_selected_keypoint(keypoint)

    def on_mouse_left_press(self, event: QMouseEvent) -> None:
        if self.annotating_state == AnnotatingState.READY:
            self.set_annotating_state(AnnotatingState.DRAWING_ANNO)

        elif self.annotating_state == AnnotatingState.DRAWING_ANNO:
            if self.quick_create:
                self.create_annotation(self.previous_label)
                self.quick_create = False
            else:
                self.create_annotation()

            self.set_annotating_state(AnnotatingState.IDLE)

        elif self.annotating_state == AnnotatingState.DRAWING_KEYPOINTS:
            self.keypoint_annotator.add_keypoint()

        else:
            self.set_annotating_state(AnnotatingState.IDLE)

            if not self.hovered_anno:
                self.set_selected_annotation(None)

            if self.hovered_keypoint:
                self.on_keypoint_left_press(self.hovered_keypoint, event)
            else:
                self.set_selected_keypoint(None)

        self.update()

    def on_mouse_right_press(self, event: QMouseEvent) -> None:
        self.set_annotating_state(AnnotatingState.IDLE)

        if self.hovered_anno:
            self.set_selected_annotation(self.hovered_anno)
            context_menu = AnnotationContextMenu(self, self.hovered_anno)

        else:
            if self.parent.annotation_list.isVisible():
                return

            context_menu = CanvasContextMenu(self)

        context_menu.exec(event.globalPosition().toPoint())
        self.update()

    def on_mouse_left_drag(self, cursor_shift: tuple[int, int]) -> None:
        if self.annotating_state == AnnotatingState.DRAWING_KEYPOINTS:
            self.keypoint_annotator.update()

        elif self.hovered_anno:
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
        if self.annotating_state == AnnotatingState.DRAWING_KEYPOINTS:
            self.keypoint_annotator.update()

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

        if self.annotating_state == AnnotatingState.DRAWING_KEYPOINTS:
            return

        if self.hovered_anno.selected == SelectionType.UNSELECTED:
            if Qt.KeyboardModifier.ControlModifier & event.modifiers():
                self.add_selected_annotation(self.hovered_anno)
            else:
                self.set_selected_annotation(self.hovered_anno)

        elif self.hovered_anno.selected == SelectionType.NEWLY_SELECTED:
            if self.hovered_anno.has_keypoints:
                self.hovered_anno.selected = SelectionType.BOX_ONLY
            elif Qt.KeyboardModifier.ControlModifier & event.modifiers():
                self.unselect_annotation(self.hovered_anno)

        self.update()

    def on_mouse_hover(self) -> None:
        if self.annotating_state in (AnnotatingState.MOVING_ANNO,
                                     AnnotatingState.MOVING_KEYPOINT):
            self.set_annotating_state(AnnotatingState.IDLE)

        elif self.annotating_state == AnnotatingState.DRAWING_KEYPOINTS:
            self.keypoint_annotator.update()

        else:
            self.set_hovered_object()

        self.update()

    def on_mouse_middle_press(self, cursor_position: tuple[int, int]) -> None:
        if not self.is_cursor_in_bounds():
            return

        self.zoom_handler.toggle_zoom(cursor_position)
        self.update()

    def on_scroll_up(self, cursor_position: tuple[int, int]) -> None:
        if not self.is_cursor_in_bounds():
            return

        self.zoom_handler.zoom_in(cursor_position)
        self.update()

    def on_scroll_down(self, cursor_position: tuple[int, int]) -> None:
        if not self.is_cursor_in_bounds():
            return

        self.zoom_handler.zoom_out(cursor_position)
        self.update()

    def on_escape(self) -> None:
        if self.parent.settings_window.isVisible():
            self.parent.settings_window.close()
            return

        self.set_annotating_state(AnnotatingState.IDLE)
        self.unselect_all()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.mouse_handler.mousePressEvent(event)

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
        painter = CanvasPainter(self)
        painter.paint_scene()
        painter.end()
