from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QToolButton

__tool_button_style__ = Qt.ToolButtonStyle.ToolButtonTextUnderIcon


class ToolBar(QToolBar):
    toolbar_actions = (
        'open_dir',
        'open_labels',
        'next_image',
        'prev_image',
        '__separator__',
        'generate',
        'import',
        'export',
        '__separator__',
        'bbox',
        'keypoints'
    )

    def __init__(self, actions: dict[str, QAction]) -> None:
        super().__init__()

        for action_name in self.toolbar_actions:
            if action_name == '__separator__':
                self.addSeparator()
                continue

            action = actions[action_name]

            button = ToolButton()
            button.setDefaultAction(action)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setToolButtonStyle(__tool_button_style__)

            self.addWidget(button)


class ToolButton(QToolButton):
    def minimumSizeHint(self) -> QSize:
        return QSize(75, 60)
