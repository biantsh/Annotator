from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from app.objects import Annotation, Keypoint

if TYPE_CHECKING:
    from app.canvas import Canvas


class Action(ABC):
    @abstractmethod
    def undo(self, annotations: list[Annotation]) -> None:
        """Generate and execute the opposite action."""

    @abstractmethod
    def redo(self, annotations: list[Annotation]) -> None:
        """Generate and re-execute the action."""


class ActionCreate(Action):
    def __init__(self,
                 parent: 'Canvas',
                 created_annos: list[tuple[list, str, list]]
                 ) -> None:
        self.parent = parent
        self.created_annos = created_annos

    def _find_annotations(self,
                          candidates: list[Annotation]
                          ) -> list[Annotation]:
        annotations = []

        for candidate in candidates:
            candidate_info = candidate.position, candidate.label_name, candidate.keypoints

            if candidate_info in self.created_annos:
                annotations.append(candidate)

        return annotations

    def undo(self, annotations: list[Annotation]) -> None:
        created_annotations = self._find_annotations(annotations)

        self.parent.annotations = [anno for anno in self.parent.annotations
                                   if anno not in created_annotations]

    def redo(self, _: list[Annotation]) -> None:
        self.parent.set_selected_annotation(None)

        for position, label, keypoints in self.created_annos:
            annotation = Annotation(position, label, keypoints)

            self.parent.annotations.append(annotation)
            self.parent.add_selected_annotation(annotation)


class ActionDelete(Action):
    def __init__(self,
                 parent: 'Canvas',
                 deleted_annos: list[tuple[list, str, list]]
                 ) -> None:
        self.parent = parent
        self.deleted_annos = deleted_annos

    def _find_annotations(self,
                          candidates: list[Annotation]
                          ) -> list[Annotation]:
        annotations = []

        for candidate in candidates:
            candidate_info = candidate.position, candidate.label_name, candidate.keypoints

            if candidate_info in self.deleted_annos:
                annotations.append(candidate)

        return annotations

    def undo(self, _: list[Annotation]) -> None:
        self.parent.set_selected_annotation(None)

        for position, label, keypoints in self.deleted_annos:
            annotation = Annotation(position, label, keypoints)

            self.parent.annotations.append(annotation)
            self.parent.add_selected_annotation(annotation)

    def redo(self, annotations: list[Annotation]) -> None:
        to_delete = self._find_annotations(annotations)

        self.parent.annotations = [anno for anno in self.parent.annotations
                                   if anno not in to_delete]


class ActionRename(Action):
    def __init__(self,
                 parent: 'Canvas',
                 renamed_annos: list[tuple[list[int, ...], str, str]]
                 ) -> None:
        self.parent = parent

        self.info_from = []
        self.info_to = []

        for position, label_before, label_after in renamed_annos:
            self.info_from.append((position, label_before))
            self.info_to.append((position, label_after))

    @staticmethod
    def _find_annotations(candidates: list[Annotation],
                          anno_info: list[tuple[list[int, ...], str]]
                          ) -> list[Annotation]:
        annotations = []

        for candidate in candidates:
            candidate_info = candidate.position, candidate.label_name

            if candidate_info in anno_info:
                annotations.append(candidate)

        return annotations

    def _execute(self,
                 annotations: list[Annotation],
                 info_before: list[tuple[list[int, ...], str]],
                 info_after: list[tuple[list[int, ...], str]]
                 ) -> None:
        annotations = self._find_annotations(annotations, info_before)
        self.parent.set_selected_annotation(None)

        for annotation in annotations:
            annotation_info = annotation.position, annotation.label_name

            index = info_before.index(annotation_info)
            label = info_after[index][1]

            annotation.label_name = label

            self.parent.add_selected_annotation(annotation)

    def undo(self, annotations: list[Annotation]) -> None:
        self._execute(annotations, self.info_to, self.info_from)

    def redo(self, annotations: list[Annotation]) -> None:
        self._execute(annotations, self.info_from, self.info_to)


class ActionMove(Action):
    def __init__(self,
                 parent: 'Canvas',
                 position_from: dict[str, list[int]],
                 position_to: dict[str, list[int]],
                 label_name: str
                 ) -> None:
        self.parent = parent
        self.position_from = position_from
        self.position_to = position_to
        self.label_name = label_name

    def _find_annotation(self,
                         candidates: list[Annotation],
                         position: list[int, ...]
                         ) -> Annotation | None:
        for candidate in candidates:
            if (candidate.position == position
                    and candidate.label_name == self.label_name):
                return candidate

        return None

    def _execute(self,
                 annotations: list[Annotation],
                 pos_before: dict[str, list[int]],
                 pos_after: dict[str, list[int]]
                 ) -> None:
        anno_pos_before = pos_before['annotation']
        anno_pos_after = pos_after['annotation']

        annotation = self._find_annotation(annotations, anno_pos_before)

        if annotation is None:
            return

        annotation.position = anno_pos_after

        if annotation.has_keypoints:
            for kpt_idx, keypoint in enumerate(annotation.keypoints):
                keypoint.position = pos_after['keypoints'][kpt_idx]

        self.parent.set_selected_annotation(annotation)

    def undo(self, annotations: list[Annotation]) -> None:
        self._execute(annotations, self.position_to, self.position_from)

    def redo(self, annotations: list[Annotation]) -> None:
        self._execute(annotations, self.position_from, self.position_to)


class ActionDeleteKeypoints(Action):
    def __init__(self,
                 parent: 'Canvas',
                 keypoints: list[tuple[list, int, tuple[list, str]]]
                 ) -> None:
        self.parent = parent
        self.keypoints = keypoints

    def _find_keypoints(self, candidates: list[Annotation]) -> list[Keypoint]:
        keypoints = []

        for anno in candidates:
            for kpt_pos, kpt_idx, (anno_pos, label_name) in self.keypoints:
                if (anno_pos, label_name) == (anno.position, anno.label_name):
                    keypoints.append(anno.keypoints[kpt_idx])

        return keypoints

    def undo(self, annotations: list[Annotation]) -> None:
        self.parent.set_selected_keypoint(None)

        for keypoint in self._find_keypoints(annotations):
            self.parent.add_selected_keypoint(keypoint)
            keypoint.visible = True

    def redo(self, annotations: list[Annotation]) -> None:
        for keypoint in self._find_keypoints(annotations):
            keypoint.visible = False


class ActionMoveKeypoint(Action):
    def __init__(self,
                 parent: 'Canvas',
                 kpt_idx: int,
                 position_from: list[int],
                 position_to: list[int],
                 position_anno: list[int],
                 label_name: str
                 ) -> None:
        self.parent = parent

        self.kpt_idx = kpt_idx
        self.position_from = position_from
        self.position_to = position_to
        self.position_anno = position_anno
        self.label_name = label_name

    def _find_keypoint(self, candidates: list[Annotation]) -> Keypoint:
        for anno in candidates:
            if anno.position == self.position_anno \
                    and anno.label_name == self.label_name:
                return anno.keypoints[self.kpt_idx]

    def _execute(self,
                 annotations: list[Annotation],
                 position: list[int]
                 ) -> None:
        keypoint = self._find_keypoint(annotations)

        keypoint.position = position
        self.parent.set_selected_keypoint(keypoint)

    def undo(self, annotations: list[Annotation]) -> None:
        self._execute(annotations, self.position_from)

    def redo(self, annotations: list[Annotation]) -> None:
        self._execute(annotations, self.position_to)


class ActionHandler:
    def __init__(self, parent: 'Canvas', image_name: str | None) -> None:
        self.parent = parent
        self.image_name = image_name

        self.undo_stack = defaultdict(lambda: deque(maxlen=30))
        self.redo_stack = defaultdict(lambda: deque(maxlen=30))

    def register_action(self, action: Action) -> None:
        if self.image_name is None:
            return

        self.undo_stack[self.image_name].append(action)
        self.redo_stack[self.image_name].clear()

    def undo(self) -> Action | None:
        actions = self.undo_stack[self.image_name]

        if len(actions) == 0:
            return None

        action = actions.pop()
        action.undo(self.parent.annotations)

        self.redo_stack[self.image_name].append(action)

        self.parent.unsaved_changes = True
        self.parent.update()

        if isinstance(action, (ActionCreate, ActionDelete)):
            self.parent.parent.annotation_list.redraw_widgets()

        return action

    def redo(self) -> Action | None:
        actions = self.redo_stack[self.image_name]

        if len(actions) == 0:
            return None

        action = actions.pop()
        action.redo(self.parent.annotations)

        self.undo_stack[self.image_name].append(action)

        self.parent.unsaved_changes = True
        self.parent.update()

        if isinstance(action, (ActionCreate, ActionDelete)):
            self.parent.parent.annotation_list.redraw_widgets()

        return action
