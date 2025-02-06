from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QHBoxLayout

if TYPE_CHECKING:
    from annotator import MainWindow


class MainScreen(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__()
        self.parent = parent

        self.canvas_layout = QHBoxLayout(self)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(0)

        self.canvas_layout.addWidget(self.parent.canvas)
        self.canvas_layout.addWidget(self.parent.annotation_list)
