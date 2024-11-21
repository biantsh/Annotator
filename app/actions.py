from functools import partial

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction


def open_dir(parent):
    print('Opening dir!')


def next_image(parent):
    print('Next image!')


def prev_image(parent):
    print('Previous image!')


actions = (
    ('open_dir', 'Ctrl+O', open_dir, 'Open', 'open.png'),
    ('next_image', 'D', next_image, 'Next', 'next.png'),
    ('prev_image', 'A', prev_image, 'Previous', 'prev.png')
)


class Actions:
    def __init__(self, parent):
        self.actions = [self._create_action(parent, *args) for args in actions]

    @staticmethod
    def _create_action(parent, name, shortcut, binding, text, icon):
        action = QAction(text, parent)
        action.setShortcut(shortcut)
        action.setObjectName(name)

        action.setIcon(QIcon(f':/{icon}'))
        action.triggered.connect(partial(binding, parent))

        return action
