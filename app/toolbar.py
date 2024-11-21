from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QToolBar, QToolButton


class ToolBar(QToolBar):
    toolbar_actions = (
        'open_dir',
        'next_image',
        'prev_image'
    )

    def __init__(self, actions):
        super().__init__()

        for action_name in self.toolbar_actions:
            action = actions[action_name]

            button = ToolButton()
            button.setDefaultAction(action)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

            self.addWidget(button)


class ToolButton(QToolButton):
    def minimumSizeHint(self):
        return QSize(70, 60)
