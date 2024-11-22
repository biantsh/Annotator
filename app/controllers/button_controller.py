from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from annotator import MainWindow


class ButtonController:
    requires_images = {
        'next_image',
        'prev_image'
    }
    requires_label_map = {
        'generate',
        'import',
        'export',
        'bbox'
    }

    def __init__(self, parent: 'MainWindow') -> None:
        self.parent = parent

    def _reset(self) -> None:
        for action_name in self.requires_images | self.requires_label_map:
            self.parent.actions[action_name].setEnabled(False)

    def set_enabled_buttons(self) -> None:
        self._reset()

        if self.parent.image_controller.num_images > 0:
            for action_name in self.requires_images:
                self.parent.actions[action_name].setEnabled(True)

            if self.parent.label_map_controller.labels:
                for action_name in self.requires_label_map:
                    self.parent.actions[action_name].setEnabled(True)
