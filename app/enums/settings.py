from enum import Enum, IntEnum


class Setting(str, Enum):
    LABEL_MAP = 'label_map'
    DEFAULT_IMAGE_DIR = 'default_image_dir'
    DEFAULT_LABEL_PATH = 'default_label_path'
    DEFAULT_IMPORT_PATH = 'default_import_path'
    DEFAULT_EXPORT_PATH = 'default_export_path'
    HIDE_KEYPOINTS = 'hide_keypoints'
    HIDDEN_CATEGORIES = 'hidden_categories'
    ADD_MISSING_BBOXES = 'add_missing_bboxes'


class SettingsLayout(IntEnum):
    MAIN = 0
    CATEGORIES = 1
