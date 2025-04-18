import copy
from uuid import uuid4

from app.enums.annotation import HoverType, SelectionType, VisibilityType
from app.controllers.label_map_controller import LabelSchema


class Bbox:
    def __init__(self, position: list[int, ...] = None) -> None:
        self.position = position or []
        self.has_bbox = bool(position)

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
                 position: list[int],
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


class Annotation(Bbox):
    def __init__(self,
                 label_schema: LabelSchema,
                 position: list[int] = None,
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
        self.visible = VisibilityType.VISIBLE
        self.hovered = HoverType.NONE
        self.highlighted = False

        self.implicit_bbox = []

    def __eq__(self, other: 'Annotation') -> bool:
        if isinstance(other, Annotation):
            return self.ref_id == other.ref_id

        return False

    def __copy__(self) -> 'Annotation':
        box_only = self.selected == SelectionType.BOX_ONLY
        keypoints = None if box_only else self.keypoints

        copied_anno = Annotation(copy.copy(self.label_schema),
                                 copy.copy(self.position),
                                 copy.deepcopy(keypoints))

        copied_anno.implicit_bbox = self.implicit_bbox.copy()

        for keypoint in copied_anno.keypoints:
            keypoint.parent = copied_anno

        return copied_anno

    @property
    def label_name(self) -> str:
        return self.label_schema.label_name

    @property
    def kpt_names(self) -> list[str]:
        return self.label_schema.kpt_names

    @property
    def has_keypoints(self) -> bool:
        return any(keypoint.visible for keypoint in self.keypoints)

    def fit_bbox_to_keypoints(self) -> None:
        if not self.has_keypoints:
            return

        kpts_x, kpts_y = zip(*(kpt.position for kpt in self.keypoints if kpt.visible))
        self.implicit_bbox = [min(kpts_x), min(kpts_y), max(kpts_x), max(kpts_y)]

    def get_hovered_type(self,
                         margin: float,
                         mouse_pos: tuple[float, float]
                         ) -> HoverType:
        pos_x, pos_y = mouse_pos

        if not self.has_bbox:
            if not self.implicit_bbox:
                return HoverType.NONE

            x_min, y_min, x_max, y_max = self.implicit_bbox

            if x_min <= pos_x <= x_max and y_min <= pos_y <= y_max:
                return HoverType.FULL

            return HoverType.NONE

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
                             margin: float,
                             mouse_pos: tuple[float, float]
                             ) -> Keypoint | None:
        pos_x, pos_y = mouse_pos

        min_distance = 2 * margin
        closest_keypoint = None

        for keypoint in self.keypoints[::-1]:
            distance_x = abs(keypoint.pos_x - pos_x)
            distance_y = abs(keypoint.pos_y - pos_y)

            if distance_x <= margin and distance_y <= margin:
                distance = distance_x + distance_y

                if distance < min_distance and keypoint.visible:
                    closest_keypoint = keypoint
                    min_distance = distance

        return closest_keypoint

    def set_schema(self, label_schema: LabelSchema) -> None:
        if self.kpt_names != label_schema.kpt_names:
            self.keypoints = [Keypoint(self, [0, 0], False)
                              for _ in label_schema.kpt_names]

        self.label_schema = label_schema

    def copy(self) -> 'Annotation':
        copied = Annotation(copy.copy(self.label_schema))
        copied.ref_id = self.ref_id

        copied.position = self.position.copy()
        copied.keypoints = copy.deepcopy(self.keypoints)

        copied.has_bbox = self.has_bbox
        copied.implicit_bbox = self.implicit_bbox.copy()

        for kpt in copied.keypoints:
            kpt.parent = copied

        return copied
