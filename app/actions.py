from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Any

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QWidget, QFileDialog

from app.enums.canvas import AnnotatingState

if TYPE_CHECKING:
    from annotator import MainWindow
    from app.canvas import Canvas


def open_dir(parent: 'MainWindow') -> None:
    image_dir_setting = 'default_image_dir'

    path = parent.settings.get(image_dir_setting)
    title = 'Select Image Directory'

    if dir_path := QFileDialog.getExistingDirectory(parent, title, path):
        parent.settings.set(image_dir_setting, dir_path)
        parent.open_dir(dir_path)


def on_next(parent: 'MainWindow') -> None:
    parent.canvas.on_next()


def on_prev(parent: 'MainWindow') -> None:
    parent.canvas.on_prev()


def open_labels(parent: 'MainWindow') -> None:
    label_path_setting = 'default_label_path'

    path = parent.settings.get(label_path_setting)
    title = 'Select Label Map'
    ext = 'JSON Files (*.json)'

    if file_path := QFileDialog.getOpenFileName(parent, title, path, ext)[0]:
        parent.settings.set(label_path_setting, file_path)
        parent.open_label_map(file_path)


def import_annos(parent: 'MainWindow') -> None:
    parent.prompt_import()


def export_annos(parent: 'MainWindow') -> None:
    parent.prompt_export()


def create_bbox(parent: 'MainWindow') -> None:
    if parent.canvas.annotating_state == AnnotatingState.IDLE:
        parent.canvas.set_annotating_state(AnnotatingState.READY)
    elif parent.canvas.annotating_state == AnnotatingState.READY:
        parent.canvas.set_annotating_state(AnnotatingState.IDLE)


def quick_create_bbox(parent: 'Canvas') -> None:
    if not parent.previous_label:
        return

    create_bbox(parent.parent)
    parent.quick_create = parent.annotating_state == AnnotatingState.READY


def create_keypoints(parent: 'MainWindow') -> None:
    if parent.canvas.annotating_state == AnnotatingState.IDLE:
        parent.canvas.set_annotating_state(AnnotatingState.DRAWING_KEYPOINTS)


def open_settings(parent: 'MainWindow') -> None:
    parent.open_settings()


def select_next(parent: 'Canvas') -> None:
    parent.select_next_annotation()


def select_all(parent: 'Canvas') -> None:
    parent.select_all()


def hide_annotations(parent: 'Canvas') -> None:
    parent.hide_annotations()


def rename_annotations(parent: 'Canvas') -> None:
    parent.rename_annotations()


def delete_annotations(parent: 'Canvas') -> None:
    parent.delete_annotations()


def copy_annotations(parent: 'Canvas') -> None:
    parent.copy_annotations()


def paste_annotations(parent: 'Canvas') -> None:
    parent.paste_annotations(replace_existing=False)


def paste_annotations_replace(parent: 'Canvas') -> None:
    parent.paste_annotations(replace_existing=True)


def undo_action(parent: 'Canvas') -> None:
    parent.action_handler.undo()


def redo_action(parent: 'Canvas') -> None:
    parent.action_handler.redo()


def escape(parent: 'Canvas') -> None:
    parent.on_escape()


__toolbar_actions__ = (
    ('open_dir', open_dir, 'Ctrl+O', 'Open', 'open.png', True),
    ('next', on_next, 'D', 'Next', 'next.png', False),
    ('prev', on_prev, 'A', 'Back', 'prev.png', False),
    ('open_labels', open_labels, 'Ctrl+L', 'Labels', 'label_map.png', True),
    ('import', import_annos, 'Ctrl+I', 'Import', 'import.png', False),
    ('export', export_annos, 'Ctrl+Return', 'Export', 'export.png', False),
    ('bbox', create_bbox, 'W', 'Box', 'bbox.png', False),
    ('keypoints', create_keypoints, 'R', 'Points', 'keypoints.png', False),
    ('settings', open_settings, 'Shift+Tab', 'Settings', 'settings.png', True)
)

__canvas_actions__ = (
    ('quick_create_bbox', quick_create_bbox, 'E'),
    ('select_next', select_next, 'Space'),
    ('select_all', select_all, 'Ctrl+A'),
    ('hide_annos', hide_annotations, 'Ctrl+H'),
    ('rename_annos', rename_annotations, 'Ctrl+R'),
    ('delete_annos', delete_annotations, 'Del'),
    ('copy_annos', copy_annotations, 'Ctrl+C'),
    ('paste_annos', paste_annotations, 'Ctrl+Shift+V'),
    ('paste_annos_replace', paste_annotations_replace, 'Ctrl+V'),
    ('undo', undo_action, 'Ctrl+Z'),
    ('redo', redo_action, 'Ctrl+Y'),
    ('escape', escape, 'Esc')
)


class Actions(ABC):
    def __init__(self, parent: QWidget, actions: tuple[tuple, ...]) -> None:
        self.actions = {action_name: self._create_action(parent, *args)
                        for action_name, *args in actions}

    @staticmethod
    @abstractmethod
    def _create_action(parent: QWidget,
                       binding: Callable,
                       shortcut: str,
                       text: str,
                       icon: str,
                       enabled: bool
                       ) -> QAction:
        raise NotImplementedError


class ToolBarActions(Actions):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent, __toolbar_actions__)

    @staticmethod
    def _create_action(parent: 'MainWindow',
                       binding: Callable,
                       shortcut: str,
                       text: str,
                       icon: str,
                       enabled: bool
                       ) -> QAction:
        action = QAction(text, parent)
        action.setShortcut(shortcut)
        action.setEnabled(enabled)

        action.setIcon(QIcon(f'icon:{icon}'))
        action.triggered.connect(lambda: binding(parent))

        return action


class CanvasActions(Actions):
    def __init__(self, parent: 'Canvas') -> None:
        super().__init__(parent, __canvas_actions__)

    @staticmethod
    def _create_action(parent: 'Canvas',
                       binding: Callable,
                       shortcut: str,
                       *args: Any
                       ) -> QAction:
        action = QAction(parent=parent)
        action.setShortcut(shortcut)
        action.triggered.connect(lambda: binding(parent))

        return action
