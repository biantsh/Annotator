from abc import ABC, abstractmethod
from collections import deque, defaultdict, OrderedDict
from typing import TYPE_CHECKING

from app.controllers.label_map_controller import LabelSchema
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
            self.parent.annotations.append(anno)
            self.parent.add_selected_annotation(anno)

    def undo(self) -> None:
        self.parent.unselect_all()

        self.parent.annotations = list(filter(
            lambda anno: anno not in self.annos, self.parent.annotations))


class ActionDelete(ActionCreate):
    def do(self) -> None:
        super().undo()

    def undo(self) -> None:
        super().do()


class ActionRename(Action):
    def __init__(self,
                 parent: 'Canvas',
                 annos: list[Annotation],
                 label_schema: LabelSchema
                 ) -> None:
        self.parent = parent

        self.schemas_from = {anno.ref_id: anno.label_schema for anno in annos}
        self.schema_to = label_schema

    def do(self) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations:
            if anno.ref_id in self.schemas_from:
                anno.set_schema(self.schema_to)
                self.parent.add_selected_annotation(anno)

    def undo(self) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations:
            if anno.ref_id in self.schemas_from:
                anno.set_schema(self.schemas_from[anno.ref_id])
                self.parent.add_selected_annotation(anno)


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

        self.pos_to_anno = anno.position
        self.pos_to_kpts = [kpt.position for kpt in anno.keypoints]

    def _execute(self,
                 pos_anno: list[int, ...],
                 pos_kpts: list[list[int, int]]
                 ) -> None:
        x_min, y_min, x_max, y_max = pos_anno

        for anno in self.parent.annotations:
            if anno.ref_id == self.ref_id:
                anno.position = [min(x_min, x_max), min(y_min, y_max),
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


class ActionCreateKeypoints(Action):
    def __init__(self, parent: 'Canvas', keypoints: list[Keypoint]) -> None:
        self.keypoints = defaultdict(lambda: [])
        self.parent = parent

        for keypoint in keypoints:
            keypoint_info = keypoint.index, keypoint.position
            self.keypoints[keypoint.parent.ref_id].append(keypoint_info)

    def _execute(self, visible: bool) -> None:
        self.parent.unselect_all()

        for anno in self.parent.annotations:
            if anno.ref_id not in self.keypoints:
                continue

            for index, position in self.keypoints[anno.ref_id]:
                keypoint = Keypoint(anno, position.copy(), visible)
                anno.keypoints[index] = keypoint

                if visible:
                    self.parent.add_selected_keypoint(keypoint)

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

    def do(self) -> None:
        self._execute(self.pos_to)

    def undo(self) -> None:
        self._execute(self.pos_from)


class ActionFlipKeypoints(Action):
    def __init__(self, parent: 'Canvas',  anno: Annotation) -> None:
        self.parent = parent
        self.ref_id = anno.ref_id

    def _execute(self) -> None:
        for anno in self.parent.annotations:
            if anno.ref_id != self.ref_id:
                continue

            for index_left, index_right in anno.label_schema.kpt_symmetry:
                keypoint_left = anno.keypoints[index_left - 1]
                keypoint_right = anno.keypoints[index_right - 1]

                anno.keypoints[index_left - 1] = keypoint_right
                anno.keypoints[index_right - 1] = keypoint_left

            self.parent.set_selected_annotation(anno)

    def do(self) -> None:
        self._execute()

    def undo(self) -> None:
        self._execute()


class ActionHandler:
    def __init__(self, parent: 'Canvas', image_name: str | None) -> None:
        self.parent = parent
        self.image_name = image_name

        self.action_cache = LRUActionCache(max_images=50, max_actions=30)

    def _execute(self, undo: bool) -> Action | None:
        if self.image_name not in self.action_cache:
            return None

        self.action_cache.move_to_end(self.image_name)
        stacks = self.action_cache[self.image_name]

        stack_from, stack_to = (stacks['undo'], stacks['redo']) \
            if undo else (stacks['redo'], stacks['undo'])

        if len(stack_from) == 0:
            return None

        action = stack_from.pop()
        stack_to.append(action)

        (action.undo if undo else action.do)()
        if isinstance(action, (ActionCreate, ActionDelete)):
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
