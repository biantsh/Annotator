from enum import IntEnum


class AnnotatingState(IntEnum):
    IDLE = 0
    READY = 1
    DRAWING = 2
    MOVING_ANNO = 3
    MOVING_KEYPOINT = 4
