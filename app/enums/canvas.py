from enum import IntEnum


class AnnotatingState(IntEnum):
    IDLE = 0
    READY = 1
    DRAWING_ANNO = 2
    DRAWING_KEYPOINTS = 3
    MOVING_ANNO = 4
    MOVING_KEYPOINT = 5
