from PyQt5.QtWidgets import QToolBar, QToolButton


class ToolBar(QToolBar):
    toolbar_actions = {
        'open_dir',
        'next_image',
        'previous_image'
    }

    def __init__(self, actions):
        super().__init__()

        for action in actions:
            if action.objectName() not in self.toolbar_actions:
                continue

            button = ToolButton()
            button.setDefaultAction(action)

            self.addWidget(button)


class ToolButton(QToolButton):
    pass
