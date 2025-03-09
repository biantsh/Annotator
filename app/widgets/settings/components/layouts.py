import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QSizePolicy,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QLabel
)

from app.widgets.settings.components.widgets import (
    ResetButton,
    CloseButton,
    FinishButton
)

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')


class TitleLayout(QHBoxLayout):
    def __init__(self, parent: 'SettingsWindow', text: str) -> None:
        super().__init__()

        title = QLabel(text)
        title.setStyleSheet('''
            color: rgb(200, 200, 200);
            font-size: 18px;
            margin-top: 7px;
            margin-left: 3px;
        ''')

        close_icon = QPixmap(os.path.join(__iconpath__, 'close.png'))
        close_button = QPushButton(QIcon(close_icon.scaled(12, 12)), None)

        close_button.clicked.connect(parent.close)
        close_button.setStyleSheet('''
            min-width: 20px;
            min-height: 20px;
            margin-right: 3px;
        ''')

        self.addWidget(title)
        self.addStretch()
        self.addWidget(close_button)


class SectionLayout(QHBoxLayout):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setContentsMargins(10, 0, 5, 0)

        title = QLabel(title)
        title.setStyleSheet('''
            color: rgb(153, 153, 153);
            font-size: 14px;
        ''')

        title.setSizePolicy(QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Minimum)

        separator = QFrame()
        separator.setStyleSheet('''
            background-color: rgb(53, 53, 53);
            max-height: 1px;
        ''')

        self.addWidget(title)
        self.addWidget(separator)


class FooterLayout(QHBoxLayout):
    def __init__(self,
                 parent: 'SettingsWindow',
                 submenu: bool = False
                 ) -> None:
        super().__init__()

        if not submenu:
            self.addWidget(ResetButton(parent))

        self.addStretch()
        self.addWidget(CloseButton(parent))
        self.addWidget(FinishButton(parent))
