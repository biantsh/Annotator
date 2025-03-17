from typing import TYPE_CHECKING

from app.enums.annotation import VisibilityType, SelectionType
from app.objects import Annotation, Keypoint

if TYPE_CHECKING:
    from app.canvas import Canvas


class VisibilityHandler:
    def __init__(self, canvas: 'Canvas') -> None:
        self.canvas = canvas

    def interactable(self, anno: Annotation) -> bool:
        return anno \
            and anno.label_name not in self.canvas.hidden_categories \
            and (anno.has_bbox or not self.canvas.keypoints_hidden)

    def hoverable(self, anno: Annotation) -> bool:
        return self.interactable(anno) and anno.visible

    def drawable(self, anno: Annotation) -> bool:
        return self.hoverable(anno) or anno.highlighted

    def interactable_kpt(self, keypoint: Keypoint) -> bool:
        return keypoint \
            and not self.canvas.keypoints_hidden \
            and self.interactable(keypoint.parent)

    def hoverable_kpt(self, keypoint: Keypoint) -> bool:
        annotator = self.canvas.keypoint_annotator

        if annotator.active and keypoint not in annotator.created_keypoints:
            return False

        return self.interactable_kpt(keypoint) \
            and keypoint.parent.visible == VisibilityType.VISIBLE

    def drawable_kpts(self, anno: Annotation) -> bool:
        if anno.highlighted:
            return True

        return anno.has_keypoints \
            and not self.canvas.keypoints_hidden \
            and anno.visible != VisibilityType.BOX_ONLY

    def has_keypoints(self, anno: Annotation) -> bool:
        if not anno.has_keypoints:
            return False

        return not (self.canvas.keypoints_hidden
                    or anno.visible == VisibilityType.BOX_ONLY)

    def has_movable_keypoints(self, anno: Annotation) -> bool:
        return self.has_keypoints(anno) \
            and anno.selected != SelectionType.BOX_ONLY
