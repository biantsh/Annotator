from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout

from app.widgets.settings.components.layouts import (
    TitleLayout,
    SectionLayout,
    FooterLayout
)

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow

__text_interaction__ = Qt.TextInteractionFlag.TextSelectableByMouse


class SettingsMenu(QVBoxLayout):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()

        self.addLayout(TitleLayout(parent, 'Settings'))
        self.addSpacing(20)

        self.addLayout(SectionLayout('Annotations'))
        self.addWidget(parent.settings_manager.setting_hide_keypoints)
        self.addWidget(parent.settings_manager.setting_hidden_categories)

        self.addLayout(SectionLayout('Exporting'))
        self.addWidget(parent.settings_manager.setting_add_missing_bboxes)

        self.addStretch()
        self.addLayout(FooterLayout(parent))
