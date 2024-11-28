from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Any

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QWidget, QFileDialog

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


def next_image(parent: 'MainWindow') -> None:
    parent.next_image()


def prev_image(parent: 'MainWindow') -> None:
    parent.prev_image()


def open_labels(parent: 'MainWindow') -> None:
    label_path_setting = 'default_label_path'

    path = parent.settings.get(label_path_setting)
    title = 'Select Label Map'
    ext = 'Text Files (*.txt)'

    if file_path := QFileDialog.getOpenFileName(parent, title, path, ext)[0]:
        parent.settings.set(label_path_setting, file_path)
        parent.open_label_map(file_path)


def generate_annos(parent: 'MainWindow') -> None:
    print('Generating detections...')


def import_annos(parent: 'MainWindow') -> None:
    import_path_setting = 'default_import_path'

    path = parent.settings.get(import_path_setting)
    title = 'Select Annotations File'
    ext = 'JSON Files (*.json)'

    if file_path := QFileDialog.getOpenFileName(parent, title, path, ext)[0]:
        parent.settings.set(import_path_setting, file_path)
        parent.import_annotations(file_path)


def export_annos(parent: 'MainWindow') -> None:
    export_path_setting = 'default_export_path'

    path = parent.settings.get(export_path_setting)
    title = 'Select Output File'
    ext = 'JSON Files (*.json)'

    if file_path := QFileDialog.getSaveFileName(parent, title, path, ext)[0]:
        parent.settings.set(export_path_setting, file_path)
        parent.export_annotations(file_path)


def create_bbox(parent: 'MainWindow') -> None:
    print('Creating bbox...')


def create_keypoints(parent: 'MainWindow') -> None:
    print('Creating keypoints...')


def delete_annotations(parent: 'Canvas') -> None:
    parent.delete_annotations()


def copy_annotations(parent: 'Canvas') -> None:
    parent.copy_annotations()


def paste_annotations(parent: 'Canvas') -> None:
    parent.paste_annotations()


def hide_annotations(parent: 'Canvas') -> None:
    parent.hide_annotations()


__toolbar_actions__ = (
    ('open_dir', open_dir, 'Ctrl+O', 'Open', 'open.png', True),
    ('next_image', next_image, 'D', 'Next', 'next.png', False),
    ('prev_image',  prev_image, 'A', 'Previous', 'prev.png', False),
    ('open_labels', open_labels, 'Ctrl+P', 'Labels', 'label_map.png', True),
    ('generate', generate_annos, 'Ctrl+G', 'Generate', 'generate.png', False),
    ('import', import_annos, 'Ctrl+I', 'Import', 'import.png', False),
    ('export', export_annos, 'Ctrl+Return', 'Export', 'export.png', False),
    ('bbox', create_bbox, 'W', 'Bbox', 'bbox.png', False),
    ('keypoints', create_keypoints, 'E', 'Keypoints', 'keypoints.png', False)
)

__canvas_actions__ = (
    ('delete_annos', delete_annotations, 'Del'),
    ('hide_annos', hide_annotations, 'Ctrl+H'),
    ('copy_annos', copy_annotations, 'Ctrl+C'),
    ('paste_annos', paste_annotations, 'Ctrl+V')
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
