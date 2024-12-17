from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QMouseEvent, QPaintEvent
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QFrame,
    QPushButton,
)

from app.utils import clip_value

__modality__ = Qt.WindowModality.NonModal
__windowtype__ = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
__background__ = Qt.WidgetAttribute.WA_TranslucentBackground


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

        close_button = QPushButton('\u2A09', self.popup)
        close_button.setFixedSize(24, 24)
        close_button.clicked.connect(self.close)

        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_layout.addWidget(close_button)

        layout.addLayout(title_layout)
        layout.addStretch()

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
