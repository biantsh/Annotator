from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap


class HomeScreen(QWidget):
    def __init__(self, path_default: str, path_alt: str) -> None:
        super().__init__()

        self.renderer = QSvgRenderer(path_default)
        self.renderer_alt = QSvgRenderer(path_alt)
        self.pixmap = QPixmap(1350, 760)

        painter = QPainter(self.pixmap)
        self.renderer.render(painter)

        self.label = QLabel(self)
        self.label.setPixmap(self.pixmap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)

        self.setLayout(self.layout)

    def set_highlighted(self, highlighted: bool) -> None:
        painter = QPainter(self.pixmap)

        (self.renderer_alt if highlighted else self.renderer).render(painter)
        self.label.setPixmap(self.pixmap)
