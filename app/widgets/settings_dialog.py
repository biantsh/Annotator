from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QFrame,
    QPushButton,
)

__windowtype__ = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
__background__ = Qt.WidgetAttribute.WA_TranslucentBackground


class SettingsWindow(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.parent = parent

        self.setWindowFlags(__windowtype__)
        self.setAttribute(__background__)

        self.setGeometry(parent.geometry())

        self.popup_widget = QFrame(self)
        self.popup_widget.setFixedSize(600, 400)

        close_button = QPushButton('\u2A09', self.popup_widget)
        close_button.setFixedSize(24, 24)
        close_button.clicked.connect(self.close)

        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_layout.addWidget(close_button)

        layout = QVBoxLayout(self.popup_widget)
        layout.addLayout(title_layout)
        layout.addStretch()

    def exec(self) -> None:
        parent = self.geometry()
        popup = self.popup_widget

        pos_x = parent.x() + (parent.width() - popup.width()) // 2
        pos_y = parent.y() + (parent.height() - popup.height()) // 2

        popup.move(pos_x, pos_y)
        super().exec()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        overlay_color = QColor(0, 0, 0, 150)
        painter.fillRect(self.rect(), overlay_color)

    def mousePressEvent(self, event):
        position = event.position().toPoint()

        if not self.popup_widget.geometry().contains(position):
            self.close()

        super().mousePressEvent(event)
