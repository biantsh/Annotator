from enum import IntEnum


class HoverType(IntEnum):
    """Enum specifying which part of an annotation is hovered.

    Values are chosen such that TOP | LEFT = TOP_LEFT, for example.
    """

    NONE = 0
    TOP = 1
    BOTTOM = 2
    LEFT = 4
    TOP_LEFT = 5
    BOTTOM_LEFT = 6
    RIGHT = 8
    TOP_RIGHT = 9
    BOTTOM_RIGHT = 10
    FULL = 16


class SelectionType(IntEnum):
    UNSELECTED = 0
    NEWLY_SELECTED = 1
    SELECTED = 2
    BOX_ONLY = 3
