from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QVBoxLayout

from app.widgets.settings.components.layouts import TitleLayout, FooterLayout

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow


class CategoriesMenu(QVBoxLayout):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()

        self.addLayout(TitleLayout(parent, 'Hidden categories'))
        self.addSpacing(20)

        self.addStretch()
        self.addLayout(FooterLayout(parent, submenu=True))
