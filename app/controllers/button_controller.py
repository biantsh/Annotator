from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from annotator import MainWindow


class ButtonController:
    image_dependent_actions = {
        'next',
        'prev',
        'import',
        'export',
        'bbox',
        'keypoints'
    }

    def __init__(self, parent: 'MainWindow') -> None:
        self.parent = parent

    def is_enabled(self, action_name: str) -> bool:
        return self.parent.toolbar_actions[action_name].isEnabled()

    def set_enabled_buttons(self) -> None:
        enabled = self.parent.image_controller.num_images > 0

        for action_name in self.image_dependent_actions:
            self.parent.toolbar_actions[action_name].setEnabled(enabled)
