from functools import partial
from typing import TYPE_CHECKING, Callable

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QFileDialog

if TYPE_CHECKING:
    from annotator import MainWindow


def open_dir(parent: 'MainWindow') -> None:
    title = 'Select Image Directory'

    if dir_path := QFileDialog.getExistingDirectory(parent, title):
        parent.open_dir(dir_path)


def open_labels(parent: 'MainWindow') -> None:
    title = 'Select Label Map'
    ext = 'Text Files (*.txt)'

    if file_path := QFileDialog.getOpenFileName(parent, title, '', ext)[0]:
        parent.open_label_map(file_path)


def next_image(parent: 'MainWindow') -> None:
    parent.next_image()


def prev_image(parent: 'MainWindow') -> None:
    parent.prev_image()


def generate_annos(parent: 'MainWindow') -> None:
    print('Generating detections...')


def import_annos(parent: 'MainWindow') -> None:
    title = 'Select Annotations File'
    ext = 'JSON Files (*.json)'

    if file_path := QFileDialog.getOpenFileName(parent, title, '', ext)[0]:
        parent.import_annotations(file_path)


def export_annos(parent: 'MainWindow') -> None:
    title = 'Select Output File'
    ext = 'JSON Files (*.json)'

    if file_path := QFileDialog.getSaveFileName(parent, title, '', ext)[0]:
        parent.export_annotations(file_path)


def create_bbox(parent: 'MainWindow') -> None:
    print('Creating bbox...')


def create_keypoints(parent: 'MainWindow') -> None:
    print('Creating keypoints...')


__actions__ = (
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


class Actions:
    def __init__(self, parent: 'MainWindow') -> None:
        self.actions = {action_name: self._create_action(parent, *args)
                        for action_name, *args in __actions__}

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
        action.triggered.connect(partial(binding, parent))

        return action
