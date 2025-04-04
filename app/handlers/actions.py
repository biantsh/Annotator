from abc import ABC, abstractmethod
from collections import deque, defaultdict, OrderedDict
from typing import TYPE_CHECKING, Callable

from app.controllers.label_map_controller import LabelSchema
from app.enums.annotation import SelectionType
from app.enums.canvas import AnnotatingState
from app.objects import Annotation, Keypoint

if TYPE_CHECKING:
    from app.canvas import Canvas


class Action(ABC):
    @abstractmethod
    def do(self) -> None:
        """Generate and (re-)execute the action."""

    @abstractmethod
    def undo(self) -> None:
        """Generate and execute the opposite action."""


class ActionCreate(Action):
    def __init__(self, parent: 'Canvas', annos: list[Annotation]) -> None:
        self.parent = parent
        self.annos = annos.copy()

    def do(self) -> None:
        self.parent.unselect_all()

        for anno in self.annos:
            created_anno = anno.copy()

            self.parent.annotations.append(created_anno)
            self.parent.add_selected_annotation(created_anno)

    def undo(self) -> None:
        self.parent.unselect_all()

        self.parent.annotations = list(filter(
            lambda anno: anno not in self.annos, self.parent.annotations))


class ActionDelete(Action):
    def __init__(self, parent: 'Canvas', annos: list[Annotation]) -> None:
        self.parent = parent
        self.annos = {anno.ref_id: anno.copy() for anno in annos}

    def do(self) -> None:
        self.parent.unselect_all()

        self.parent.annotations = [anno for anno in self.parent.annotations
                                   if anno.ref_id not in self.annos]

    def undo(self) -> None:
        self.parent.unselect_all()

        for anno in self.annos.values():
            if anno in self.parent.annotations:
                self.parent.annotations.remove(anno)

            self.parent.annotations.append(anno.copy())
            self.parent.add_selected_annotation(anno)


class ActionRename(Action):
    def __init__(self,
                 parent: 'Canvas',
                 annos: list[Annotation],
                 label_schema: LabelSchema
                 ) -> None:
        self.parent = parent

        self.schemas_from = {anno.ref_id: anno.label_schema for anno in annos}
        self.schema_to = label_schema

    def _execute(self, get_target_schema: Callable) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations.copy():
            if anno.ref_id in self.schemas_from:
                anno.set_schema(get_target_schema(anno.ref_id))
                self.parent.add_selected_annotation(anno)

    def do(self) -> None:
        self._execute(lambda _: self.schema_to)

    def undo(self) -> None:
        self._execute(lambda ref_id: self.schemas_from[ref_id])


class ActionMove(Action):
    def __init__(self,
                 parent: 'Canvas',
                 anno: Annotation,
                 pos_from_anno: list[int, ...],
                 pos_from_kpts: list[list[int, int]] = None
                 ) -> None:
        self.parent = parent
        self.ref_id = anno.ref_id

        self.pos_from_anno = pos_from_anno
        self.pos_from_kpts = pos_from_kpts

        self.pos_to_anno = anno.position or anno.implicit_bbox
        self.pos_to_kpts = [kpt.position for kpt in anno.keypoints]

    def _execute(self,
                 pos_anno: list[int, ...],
                 pos_kpts: list[list[int, int]]
                 ) -> None:
        x_min, y_min, x_max, y_max = pos_anno

        for anno in self.parent.annotations.copy():
            if anno.ref_id == self.ref_id:
                if anno.has_bbox:
                    anno.position = [min(x_min, x_max), min(y_min, y_max),
                                     max(x_min, x_max), max(y_min, y_max)]
                else:
                    anno.implicit_bbox = [min(x_min, x_max), min(y_min, y_max),
                                          max(x_min, x_max), max(y_min, y_max)]

                if pos_kpts:
                    for keypoint, pos in zip(anno.keypoints, pos_kpts):
                        keypoint.position = pos.copy()

                if not anno.selected:
                    self.parent.set_selected_annotation(anno)

            else:
                self.parent.unselect_annotation(anno)

    def do(self) -> None:
        self._execute(self.pos_to_anno, self.pos_to_kpts)

    def undo(self) -> None:
        self._execute(self.pos_from_anno, self.pos_from_kpts)


class ActionAddBbox(Action):
    def __init__(self, parent: 'Canvas', annos: list[Annotation]) -> None:
        self.parent = parent
        self.ref_ids = {anno.ref_id for anno in annos}

    def do(self) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations.copy():
            if anno.ref_id in self.ref_ids:
                anno.position = anno.implicit_bbox.copy()
                anno.has_bbox = True

                self.parent.add_selected_annotation(anno)

    def undo(self) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations.copy():
            if anno.ref_id in self.ref_ids:
                anno.position = []
                anno.has_bbox = False

                self.parent.add_selected_annotation(anno)


class ActionDeleteBbox(Action):
    def __init__(self, parent: 'Canvas', annos: list[Annotation]) -> None:
        self.parent = parent
        self.annos = {anno.ref_id: anno.copy() for anno in annos}

    def do(self) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations.copy():
            if anno.ref_id in self.annos:
                anno.position = []
                anno.has_bbox = False
                anno.fit_bbox_to_keypoints()

    def undo(self) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations.copy():
            if anno.ref_id in self.annos:
                anno.position = self.annos[anno.ref_id].position.copy()
                anno.has_bbox = True

                self.parent.add_selected_annotation(anno)
                anno.selected = SelectionType.BOX_ONLY


class ActionCreateKeypoints(Action):
    def __init__(self, parent: 'Canvas', keypoints: list[Keypoint]) -> None:
        self.keypoints = defaultdict(lambda: [])
        self.parent = parent

        for keypoint in keypoints:
            keypoint_info = keypoint.index, keypoint.position
            self.keypoints[keypoint.parent.ref_id].append(keypoint_info)

        self.annotations = {kpt.parent.ref_id: kpt.parent.copy()
                            for kpt in keypoints}

    def _execute(self, visible: bool) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations:
            if anno.ref_id not in self.keypoints:
                continue

            for index, position in self.keypoints[anno.ref_id]:
                anno.keypoints[index].position = position.copy()
                anno.keypoints[index].visible = visible

                if visible:
                    self.parent.add_selected_keypoint(anno.keypoints[index])

            if not anno.has_bbox:
                if anno.has_keypoints:
                    anno.fit_bbox_to_keypoints()

                else:
                    self.parent.annotations = list(
                        filter(lambda a: a != anno, self.parent.annotations))

        for anno in self.annotations.values():
            if visible and anno not in self.parent.annotations:
                self.parent.annotations.append(anno.copy())

    def do(self) -> None:
        self._execute(True)

    def undo(self) -> None:
        self._execute(False)


class ActionDeleteKeypoints(ActionCreateKeypoints):
    def do(self) -> None:
        self._execute(False)

    def undo(self) -> None:
        self._execute(True)


class ActionMoveKeypoint(Action):
    def __init__(self,
                 parent: 'Canvas',
                 keypoint: Keypoint,
                 pos_from: list[int, int]
                 ) -> None:
        self.parent = parent
        self.ref_id = keypoint.parent.ref_id

        self.pos_from = pos_from
        self.pos_to = keypoint.position
        self.index = keypoint.index

    def _execute(self, pos: list[int, int]) -> None:
        for anno in self.parent.annotations:
            if anno.ref_id == self.ref_id:
                keypoint = anno.keypoints[self.index]

                keypoint.position = pos
                self.parent.set_selected_keypoint(keypoint)

                anno.fit_bbox_to_keypoints()

    def do(self) -> None:
        self._execute(self.pos_to)

    def undo(self) -> None:
        self._execute(self.pos_from)


class ActionFlipKeypoints(Action):
    def __init__(self, parent: 'Canvas',  anno: Annotation) -> None:
        self.parent = parent
        self.ref_id = anno.ref_id

    def _execute(self) -> None:
        for anno in self.parent.annotations.copy():
            if anno.ref_id != self.ref_id:
                continue

            for index_left, index_right in anno.label_schema.kpt_symmetry:
                keypoint_left = anno.keypoints[index_left - 1]
                keypoint_right = anno.keypoints[index_right - 1]

                keypoint_left.visible, keypoint_right.visible = \
                    keypoint_right.visible, keypoint_left.visible

                keypoint_left.position, keypoint_right.position = \
                    keypoint_right.position, keypoint_left.position

            self.parent.set_selected_annotation(anno)

    def do(self) -> None:
        self._execute()

    def undo(self) -> None:
        self._execute()


class ActionHandler:
    def __init__(self, parent: 'Canvas', image_name: str | None) -> None:
        self.parent = parent
        self.image_name = image_name

        self.action_cache = LRUActionCache(max_images=50, max_actions=50)

    def _execute(self, undo: bool) -> Action | None:
        if self.image_name not in self.action_cache:
            return None

        self.parent.set_annotating_state(AnnotatingState.IDLE)
        self.action_cache.move_to_end(self.image_name)
        stacks = self.action_cache[self.image_name]

        stack_from, stack_to = (stacks['undo'], stacks['redo']) \
            if undo else (stacks['redo'], stacks['undo'])

        if len(stack_from) == 0:
            return None

        action = stack_from.pop()
        stack_to.append(action)

        action.undo() if undo else action.do()

        self.parent.parent.annotation_list.redraw_widgets()
        self.parent.unsaved_changes = True
        self.parent.update()

        return action

    def undo(self) -> Action | None:
        return self._execute(undo=True)

    def redo(self) -> Action | None:
        return self._execute(undo=False)

    def register_action(self, action: Action) -> None:
        self.action_cache.add_image(self.image_name)

        self.action_cache[self.image_name]['redo'].clear()
        self.action_cache[self.image_name]['redo'].append(action)

        self._execute(undo=False)


class LRUActionCache(OrderedDict):
    def __init__(self, max_images: int, max_actions: int) -> None:
        super().__init__()

        self.max_images = max_images
        self.max_actions = max_actions

    def add_image(self, image_name: str) -> None:
        if image_name in self:
            self.move_to_end(image_name)

        else:
            if len(self) == self.max_images:
                self.popitem(last=False)

            self[image_name] = {
                'undo': deque(maxlen=self.max_actions),
                'redo': deque(maxlen=self.max_actions)
            }
