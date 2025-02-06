from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel

if TYPE_CHECKING:
    from annotator import MainWindow


class Toast(QLabel):
    def __init__(self, parent: 'MainWindow', message: str) -> None:
        super().__init__(message, parent)

        self.adjustSize()
        self.hide()

        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.close)

    def show(self):
        self.move((self.parent().width() - self.width()) // 2, 50)
        super().show()

        self.close_timer.start(2500)
