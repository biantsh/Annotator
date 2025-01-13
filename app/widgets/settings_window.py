from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QObject, QEvent, QPoint
from PyQt6.QtGui import QPainter, QColor, QMouseEvent, QPaintEvent
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

from app.utils import clip_value

if TYPE_CHECKING:
    from annotator import MainWindow

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
        layout = QVBoxLayout(self.popup)

        layout.addLayout(TitleLayout(self))
        layout.addSpacing(20)

        layout.addLayout(SectionLayout('Export'))
        setting_add_missing_bboxes = SettingAddMissingBboxes(self)

        layout.addWidget(setting_add_missing_bboxes)
        self.checkboxes.append(setting_add_missing_bboxes)

        layout.addStretch()

        close_layout = QHBoxLayout()
        layout.addLayout(close_layout)

        close_layout.addWidget(ResetButton(self))
        close_layout.addStretch()
        close_layout.addWidget(CloseButton(self))
        close_layout.addWidget(FinishButton(self))

    def show(self) -> None:
        self.setGeometry(self.parent.frameGeometry())

        window = self.rect()
        popup = self.popup

        pos_x = (window.width() - popup.width()) // 2
        pos_y = (window.height() - popup.height()) // 2

        popup.move(pos_x, pos_y)

        super().show()
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
            margin-top: 5px;
            margin-left: 3px;
        ''')

        close_button = QPushButton('\u2A09', parent.popup)
        close_button.clicked.connect(parent.close)
        close_button.setFixedSize(24, 24)

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


class SettingAddMissingBboxes(QWidget):
    default = False

    def __init__(self, parent: SettingsWindow) -> None:
        super().__init__()

        self.parent = parent
        self.checkbox = QCheckBox('Add missing boxes')

        toggled = parent.parent.settings.get('add_missing_bboxes')
        self.checkbox.setChecked(toggled)

        self.checkbox.stateChanged.connect(
            lambda: self.set_checked(self.checkbox.isChecked()))
        self.checkbox.installEventFilter(self)

        label = QLabel('Automatically adds missing boxes '
                       'by outlining the keypoints')
        label.setTextInteractionFlags(__text_interaction__)

        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.checkbox)
        layout.addStretch()
        layout.addWidget(label)

    def set_checked(self, checked: bool) -> None:
        self.parent.parent.settings.set('add_missing_bboxes', checked)
        self.checkbox.setChecked(checked)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() == event.Type.Enter:
            source.setStyleSheet('''::indicator {
                border: 1px solid rgb(60, 120, 216);
            }''')

        elif event.type() == event.Type.Leave:
            source.setStyleSheet('')

        return False


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
