from typing import TYPE_CHECKING

from PyQt6.QtCore import (
    QObject,
    QEvent,
    QRect,
    QPropertyAnimation,
    QEasingCurve
)
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QWidget, QCheckBox, QPushButton, QScrollArea

from app.enums.settings import Setting, SettingsLayout
from app.styles.style_sheets import SettingCheckBoxStyleSheet
from app.utils import clip_value
from app.widgets.message_box import ConfirmResetSettingsBox

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow


class SettingCheckBox(QCheckBox):
    def __init__(self,
                 parent: 'SettingsWindow',
                 setting_id: Setting,
                 text: str,
                 default: bool,
                 ) -> None:
        super().__init__(text)

        self.parent = parent
        self.settings = parent.parent.settings

        self.setting_id = setting_id
        self.default = default

        self.installEventFilter(self)
        self.setChecked(self.settings.get(setting_id))
        self.stateChanged.connect(lambda: self.set_checked(self.isChecked()))

        self._refresh()

    def _refresh(self) -> None:
        hovered, checked = self.underMouse(), self.isChecked()
        self.setStyleSheet(str(SettingCheckBoxStyleSheet(hovered, checked)))

    def set_checked(self, checked: bool) -> None:
        self.settings.set(self.setting_id, checked)
        self.setChecked(checked)

        self.parent.parent.canvas.update()
        self._refresh()

    def eventFilter(self, _: QObject, event: QEvent) -> bool:
        if event.type() in (event.Type.Enter, event.Type.Leave):
            self._refresh()

        return False


class SettingButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)


class ResetButton(QPushButton):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__('Reset')

        self.parent = parent
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        if ConfirmResetSettingsBox(self.parent.parent).exec():
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


class ScrollableArea(QScrollArea):
    def __init__(self) -> None:
        super().__init__()

        scroll_bar = self.verticalScrollBar()
        self._animation = QPropertyAnimation(scroll_bar, b'value')
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def is_in_view(self, widget: QWidget) -> bool:
        viewport = self.viewport()

        top_left = widget.mapTo(viewport, widget.rect().topLeft())
        bottom_right = widget.mapTo(viewport, widget.rect().bottomRight())

        return viewport.rect().intersects(QRect(top_left, bottom_right))

    def can_scroll_to_widget(self, widget: QWidget) -> bool:
        target_point = widget.mapTo(self.widget(), widget.rect().topLeft())
        return target_point.y() <= self.verticalScrollBar().maximum()

    def scroll_to_widget(self, widget: QWidget) -> None:
        target_point = widget.mapTo(self.widget(), widget.rect().topLeft())
        self.scroll_to_value(target_point.y())

    def scroll_to_value(self, value: int) -> None:
        if self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()

        self._animation.setStartValue(self.verticalScrollBar().value())
        self._animation.setEndValue(value)
        self._animation.start()

    def wheelEvent(self, event: QWheelEvent) -> None:
        scroll_bar = self.verticalScrollBar()
        minimum, maximum = scroll_bar.minimum(), scroll_bar.maximum()

        delta = event.angleDelta().y()
        delta = clip_value(delta, -120, 120)

        target_value = scroll_bar.value() - delta
        target_value = clip_value(target_value, minimum, maximum)

        self.scroll_to_value(target_value)
