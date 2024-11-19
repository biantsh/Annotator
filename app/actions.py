from functools import partial

from PyQt5.QtWidgets import QAction


def open_dir(parent):
    print('Opening dir!')


def next_image(parent):
    print('Next image!')


def previous_image(parent):
    print('Previous image!')


actions = (
    ('open_dir', 'Ctrl+O', open_dir, 'Open Directory'),
    ('next_image', 'Ctrl+D', next_image, 'Next Image'),
    ('previous_image', 'Ctrl+A', previous_image, 'Previous Image')
)


class Actions:
    def __init__(self, parent):
        self.actions = [self._create_action(parent, *args) for args in actions]

    @staticmethod
    def _create_action(parent, name, shortcut, binding, text):
        action = QAction(text, parent)
        action.setShortcut(shortcut)
        action.setObjectName(name)

        action.triggered.connect(partial(binding, parent))

        return action
