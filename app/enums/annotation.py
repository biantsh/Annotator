from enum import IntEnum


class AnnotatingState(IntEnum):
    IDLE = 0
    READY = 1
    DRAWING = 2


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


# Define which areas to highlight depending on the hover type
HOVER_AREAS = {
    HoverType.FULL: {'full'},
    HoverType.TOP: {'top', 'top_left', 'top_right'},
    HoverType.LEFT: {'left', 'top_left', 'bottom_left'},
    HoverType.RIGHT: {'right', 'top_right', 'bottom_right'},
    HoverType.BOTTOM: {'bottom', 'bottom_left', 'bottom_right'}
}
