from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QMouseEvent, QPaintEvent
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy
)

from app.utils import clip_value

__modality__ = Qt.WindowModality.NonModal
__windowtype__ = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
__background__ = Qt.WidgetAttribute.WA_TranslucentBackground

__size_policy__ = QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum


class SettingsWindow(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.parent = parent

        self.setWindowModality(__modality__)
        self.setWindowFlags(__windowtype__)
        self.setAttribute(__background__)

        self.popup = QFrame(self)
        self.popup.setFixedSize(600, 400)

        self.dragging = False
        self.drag_offset = QPoint()

        self.build_layout()

    def build_layout(self) -> None:
        layout = QVBoxLayout(self.popup)

        layout.addLayout(TitleLayout(self))
        layout.addSpacing(20)

        layout.addLayout(SectionLayout('Appearance'))
        layout.addSpacing(60)

        layout.addLayout(SectionLayout('Miscellaneous'))
        layout.addStretch()

        label = QLabel('Note: there are currently no settings available.')
        label.setStyleSheet('color: rgb(153, 153, 153);')
        label.setContentsMargins(3, 0, 0, 3)
        layout.addWidget(label)

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
        self.setContentsMargins(10, 0, 5, 10)

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
