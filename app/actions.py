from functools import partial

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QFileDialog


def open_dir(parent):
    if dir_path := QFileDialog.getExistingDirectory(parent):
        parent.open_dir(dir_path)


def next_image(parent):
    parent.next_image()


def prev_image(parent):
    parent.prev_image()


actions = (
    ('open_dir', 'Ctrl+O', open_dir, 'Open', 'open.png', True),
    ('next_image', 'D', next_image, 'Next', 'next.png', False),
    ('prev_image', 'A', prev_image, 'Previous', 'prev.png', False)
)


class Actions:
    def __init__(self, parent):
        self.actions = {action_name: self._create_action(parent, *args)
                        for action_name, *args in actions}

    @staticmethod
    def _create_action(parent, shortcut, binding, text, icon, enabled):
        action = QAction(text, parent)
        action.setShortcut(shortcut)
        action.setEnabled(enabled)

        action.setIcon(QIcon(f'icon:{icon}'))
        action.triggered.connect(partial(binding, parent))

        return action
