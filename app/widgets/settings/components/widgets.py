from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtWidgets import QCheckBox, QPushButton

from app.enums.settings import SettingsLayout
from app.styles.style_sheets import SettingCheckBoxStyleSheet

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow


class SettingCheckBox(QCheckBox):
    def __init__(self,
                 parent: 'SettingsWindow',
                 setting_id: str,
                 text: str,
                 default: bool,
                 ) -> None:
        super().__init__(text)

        self.parent = parent
        self.setting_id = setting_id
        self.default = default

        self.installEventFilter(self)
        self.setChecked(parent.parent.settings.get(setting_id))
        self.stateChanged.connect(lambda: self.set_checked(self.isChecked()))

        self._refresh()

    def _refresh(self) -> None:
        hovered, checked = self.underMouse(), self.isChecked()
        self.setStyleSheet(str(SettingCheckBoxStyleSheet(hovered, checked)))

    def set_checked(self, checked: bool) -> None:
        self.parent.parent.settings.set(self.setting_id, checked)
        self.setChecked(checked)

        self.parent.parent.canvas.update()
        self._refresh()

    def eventFilter(self, _: QObject, event: QEvent) -> bool:
        if event.type() in (event.Type.Enter, event.Type.Leave):
            self._refresh()

        return False


class SettingButton(QPushButton):
    def __init__(self, parent: 'SettingsWindow', text: str) -> None:
        super().__init__(text)
        self.parent = parent


class ResetButton(QPushButton):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__('Reset')

        self.parent = parent
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        self.parent.settings_manager.reset()


class CloseButton(QPushButton):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__('Close')

        self.parent = parent
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        main_menu = self.parent.layouts[SettingsLayout.MAIN]

        if self.parent.layout.currentWidget() is main_menu:
            self.parent.close()
        else:
            self.parent.layout.setCurrentWidget(main_menu)


class FinishButton(QPushButton):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__('OK')

        self.parent = parent
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        self.parent.close()
