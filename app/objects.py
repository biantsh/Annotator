import copy
from uuid import uuid4

from app.enums.annotation import HoverType, SelectionType
from app.controllers.label_map_controller import LabelSchema


class Bbox:
    def __init__(self, position: list[int, ...]) -> None:
        self.position = position

    @property
    def xywh(self) -> tuple[int, ...]:
        return self.left, self.top, self.width, self.height

    @property
    def left(self) -> int:
        return self.position[0]

    @property
    def top(self) -> int:
        return self.position[1]

    @property
    def right(self) -> int:
        return self.position[2]

    @property
    def bottom(self) -> int:
        return self.position[3]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height


class Keypoint:
    def __init__(self,
                 parent: 'Annotation',
                 position: list[int, ...],
                 visible: bool = True
                 ) -> None:
        self.parent = parent
        self.position = position
        self.visible = visible

        self.hovered = False
        self.selected = False

    @property
    def index(self) -> int:
        return self.parent.keypoints.index(self)

    @property
    def pos_x(self) -> int:
        return self.position[0]

    @property
    def pos_y(self) -> int:
        return self.position[1]

    def get_hovered(self, mouse_position: tuple[int, int]) -> bool:
        pos_x, pos_y = mouse_position
        margin = 5

        return abs(self.pos_x - pos_x) <= margin \
            and abs(self.pos_y - pos_y) <= margin


class Annotation(Bbox):
    def __init__(self,
                 position: list[int, ...],
                 label_schema: LabelSchema,
                 keypoints: list[Keypoint] = None,
                 ref_id: str = None
                 ) -> None:
        super().__init__(position)

        self.label_schema = label_schema
        self.ref_id = ref_id or uuid4().hex

        self.keypoints = keypoints or [
            Keypoint(self, [0, 0], False)
            for _ in label_schema.kpt_names]

        self.selected = SelectionType.UNSELECTED
        self.hovered = HoverType.NONE
        self.highlighted = False
        self.hidden = False

    def __eq__(self, other: 'Annotation') -> bool:
        if isinstance(other, Annotation):
            return self.ref_id == other.ref_id

        return False

    def __copy__(self) -> 'Annotation':
        box_only = self.selected == SelectionType.BOX_ONLY
        keypoints = None if box_only else self.keypoints

        copied_anno = Annotation(copy.copy(self.position),
                                 copy.copy(self.label_schema),
                                 copy.deepcopy(keypoints))

        for keypoint in copied_anno.keypoints:
            keypoint.parent = copied_anno

        return copied_anno

    @classmethod
    def from_xywh(cls,
                  position: list[int, ...],
                  label_schema: LabelSchema
                  ) -> 'Annotation':
        x_min, y_min, width, height = position
        x_max, y_max = x_min + width, y_min + height

        return cls([x_min, y_min, x_max, y_max], label_schema)

    @property
    def label_name(self) -> str:
        return self.label_schema.label_name

    @property
    def kpt_names(self) -> list[str]:
        return self.label_schema.kpt_names

    @property
    def has_keypoints(self) -> bool:
        return any(keypoint.visible for keypoint in self.keypoints)

    def get_hovered_type(self, mouse_pos: tuple[int, int]) -> HoverType:
        pos_x, pos_y = mouse_pos
        margin = 5

        if not (self.left - margin <= pos_x <= self.right + margin and
                self.top - margin <= pos_y <= self.bottom + margin):
            return HoverType.NONE

        top = abs(pos_y - self.top) <= margin
        left = abs(pos_x - self.left) <= margin
        right = abs(pos_x - self.right) <= margin
        bottom = abs(pos_y - self.bottom) <= margin

        hover_type = HoverType.NONE
        hover_type |= top and HoverType.TOP
        hover_type |= left and HoverType.LEFT
        hover_type |= right and HoverType.RIGHT
        hover_type |= bottom and HoverType.BOTTOM

        if not (hover_type and hover_type in set(HoverType)):
            return HoverType.FULL

        return hover_type

    def get_hovered_keypoint(self,
                             mouse_pos: tuple[int, int]
                             ) -> Keypoint | None:
        for keypoint in self.keypoints[::-1]:
            if keypoint.visible and keypoint.get_hovered(mouse_pos):
                return keypoint

    def set_schema(self, label_schema: LabelSchema) -> None:
        if self.kpt_names != label_schema.kpt_names:
            self.keypoints = [Keypoint(self, [0, 0], False)
                              for _ in label_schema.kpt_names]

        self.label_schema = label_schema
