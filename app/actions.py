from functools import partial
from typing import TYPE_CHECKING, Callable

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QFileDialog

if TYPE_CHECKING:
    from annotator import MainWindow


def open_dir(parent: 'MainWindow') -> None:
    if dir_path := QFileDialog.getExistingDirectory(parent):
        parent.open_dir(dir_path)


def next_image(parent: 'MainWindow') -> None:
    parent.next_image()


def prev_image(parent: 'MainWindow') -> None:
    parent.prev_image()


actions = (
    ('open_dir', open_dir, 'Ctrl+O', 'Open', 'open.png', True),
    ('next_image', next_image, 'D', 'Next', 'next.png', False),
    ('prev_image',  prev_image, 'A', 'Previous', 'prev.png', False)
)


class Actions:
    def __init__(self, parent: 'MainWindow') -> None:
        self.actions = {action_name: self._create_action(parent, *args)
                        for action_name, *args in actions}

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
