from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QLabel

from app.enums.settings import Setting, SettingsLayout
from app.widgets.settings.components.widgets import (
    SettingCheckBox,
    SettingButton
)

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow

__text_interaction__ = Qt.TextInteractionFlag.TextSelectableByMouse


class SettingsManager:
    def __init__(self, parent: 'SettingsWindow') -> None:
        self.setting_hide_keypoints = SettingHideKeypoints(parent)
        self.setting_hidden_categories = SettingSetHiddenCategories(parent)
        self.setting_add_missing_bboxes = SettingAddMissingBboxes(parent)

        self.settings = [
            self.setting_hide_keypoints,
            self.setting_hidden_categories,
            self.setting_add_missing_bboxes
        ]

    def reset(self) -> None:
        for setting in self.settings:
            setting.reset()


class SettingHideKeypoints(QWidget):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()

        self.checkbox = SettingCheckBox(
            parent, Setting.HIDE_KEYPOINTS, 'Hide keypoints', False)

        self.checkbox.clicked.connect(
            lambda: parent.parent.annotation_list.redraw_widgets())

        label = QLabel('Hide keypoints across all annotations')
        label.setTextInteractionFlags(__text_interaction__)

        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.checkbox)
        layout.addStretch()
        layout.addWidget(label)

        layout.setContentsMargins(11, 11, 11, 0)

    def reset(self) -> None:
        self.checkbox.set_checked(self.checkbox.default)


class SettingSetHiddenCategories(QWidget):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()
        self.parent = parent

        self.settings = parent.parent.settings
        self.categories = set(self.settings.get(Setting.HIDDEN_CATEGORIES))

        self.button = SettingButton('Hide Categories...')
        self.button.clicked.connect(lambda: parent.set_layout(
            SettingsLayout.CATEGORIES))

        label = QLabel('Select categories to hide/show across sessions')
        label.setTextInteractionFlags(__text_interaction__)

        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.button)
        layout.addStretch()
        layout.addWidget(label)

        layout.setContentsMargins(11, 0, 11, 11)

    def reset(self) -> None:
        self.categories.clear()
        self.settings.set(Setting.HIDDEN_CATEGORIES, [])

        canvas = self.parent.parent.canvas
        canvas.parent.annotation_list.redraw_widgets()
        canvas.update()


class SettingAddMissingBboxes(QWidget):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()

        self.checkbox = SettingCheckBox(
            parent, Setting.ADD_MISSING_BBOXES, 'Add missing boxes', False)

        label = QLabel('Generate missing boxes by outlining the keypoints')
        label.setTextInteractionFlags(__text_interaction__)

        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.checkbox)
        layout.addStretch()
        layout.addWidget(label)

    def reset(self) -> None:
        self.checkbox.set_checked(self.checkbox.default)
