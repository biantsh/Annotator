import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent, QPoint
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPixmap,
    QIcon,
    QMouseEvent,
    QPaintEvent
)
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QCheckBox,
    QSizePolicy
)

from app.styles.style_sheets import SettingCheckBoxStyleSheet
from app.utils import clip_value

if TYPE_CHECKING:
    from annotator import MainWindow

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')

__modality__ = Qt.WindowModality.NonModal
__windowtype__ = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
__text_interaction__ = Qt.TextInteractionFlag.TextSelectableByMouse
__background__ = Qt.WidgetAttribute.WA_TranslucentBackground

__size_policy__ = QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum


class SettingsWindow(QDialog):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.parent = parent

        self.setWindowModality(__modality__)
        self.setWindowFlags(__windowtype__)
        self.setAttribute(__background__)

        self.popup = QFrame(self)
        self.popup.setFixedSize(600, 400)

        self.dragging = False
        self.drag_offset = QPoint()

        self.checkboxes = []
        self.build_layout()

    def build_layout(self) -> None:
        setting_hide_keypoints = SettingHideKeypoints(self)
        setting_add_missing_bboxes = SettingAddMissingBboxes(self)

        self.checkboxes.append(setting_hide_keypoints.checkbox)
        self.checkboxes.append(setting_add_missing_bboxes.checkbox)

        layout = QVBoxLayout(self.popup)
        layout.addLayout(TitleLayout(self))
        layout.addSpacing(20)

        layout.addLayout(SectionLayout('Annotations'))
        layout.addWidget(setting_hide_keypoints)
        layout.addWidget(SettingSetHiddenCategories(self))

        layout.addLayout(SectionLayout('Exporting'))
        layout.addWidget(setting_add_missing_bboxes)

        layout.addStretch()

        close_layout = QHBoxLayout()
        layout.addLayout(close_layout)

        close_layout.addWidget(ResetButton(self))
        close_layout.addStretch()
        close_layout.addWidget(CloseButton(self))
        close_layout.addWidget(FinishButton(self))

    def show(self) -> None:
        self.setGeometry(self.parent.frameGeometry())

        pos_x = (self.width() - self.popup.width()) // 2
        pos_y = (self.height() - self.popup.height()) // 2
        self.popup.move(pos_x, pos_y)

        super().showFullScreen() if self.parent.isFullScreen() \
            else super().showNormal()

        self.activateWindow()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        position = event.position().toPoint()
        global_position = event.globalPosition().toPoint()

        if not self.popup.geometry().contains(position):
            self.close()

        elif event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_offset = global_position - self.popup.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.dragging:
            return

        new_pos = event.globalPosition().toPoint() - self.drag_offset
        x_pos, y_pos = new_pos.x(), new_pos.y()

        window = self.rect()
        popup = self.popup

        x_pos = clip_value(x_pos, 0, window.width() - popup.width())
        y_pos = clip_value(y_pos, 0, window.height() - popup.height())

        popup.move(x_pos, y_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.dragging = False

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        overlay_color = QColor(0, 0, 0, 150)
        painter.fillRect(self.rect(), overlay_color)


class TitleLayout(QHBoxLayout):
    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__()

        title = QLabel('Settings')
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
        title.setSizePolicy(*__size_policy__)

        separator = QFrame()
        separator.setStyleSheet('''
            background-color: rgb(53, 53, 53);
            max-height: 1px;
        ''')

        self.addWidget(title)
        self.addWidget(separator)


class SettingCheckBox(QCheckBox):
    def __init__(self,
                 parent: SettingsWindow,
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

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() in (event.Type.Enter, event.Type.Leave):
            self._refresh()

        return False


class SettingButton(QPushButton):
    def __init__(self, parent: SettingsWindow, text: str) -> None:
        super().__init__(text)
        self.parent = parent


class SettingHideKeypoints(QWidget):
    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__()
        self.parent = parent

        self.checkbox = SettingCheckBox(
            parent, 'hide_keypoints', 'Hide keypoints', False)

        label = QLabel('Hide keypoints across all annotations')
        label.setTextInteractionFlags(__text_interaction__)

        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.checkbox)
        layout.addStretch()
        layout.addWidget(label)

        layout.setContentsMargins(11, 11, 11, 0)


class SettingSetHiddenCategories(QWidget):
    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__()
        self.parent = parent

        self.button = SettingButton(
            parent, 'Hide Categories...')

        label = QLabel('Select categories to hide/show across sessions')
        label.setTextInteractionFlags(__text_interaction__)

        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.button)
        layout.addStretch()
        layout.addWidget(label)

        layout.setContentsMargins(11, 0, 11, 11)


class SettingAddMissingBboxes(QWidget):
    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__()
        self.parent = parent

        self.checkbox = SettingCheckBox(
            parent, 'add_missing_bboxes', 'Add missing boxes', False)

        label = QLabel('Generate missing boxes by outlining the keypoints')
        label.setTextInteractionFlags(__text_interaction__)

        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.checkbox)
        layout.addStretch()
        layout.addWidget(label)


class ResetButton(QPushButton):
    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__('Reset')

        self.parent = parent
        self.clicked.connect(self.reset)

    def reset(self) -> None:
        for checkbox in self.parent.checkboxes:
            checkbox.set_checked(checkbox.default)


class CloseButton(QPushButton):
    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__('Close')
        self.clicked.connect(parent.close)


class FinishButton(QPushButton):
    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__('OK')
        self.clicked.connect(parent.close)
