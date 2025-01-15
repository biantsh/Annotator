from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class HomeScreen(QWidget):
    def __init__(self, path_default: str, path_alt: str) -> None:
        super().__init__()
        self.svg_size = 1350, 760

        self.renderer_default = QSvgRenderer(path_default)
        self.renderer_alt = QSvgRenderer(path_alt)
        self.renderer = self.renderer_default

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.layout)

        self._update_pixmap()

    def _update_pixmap(self) -> None:
        pixmap = QPixmap(self.width(), self.height())
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        svg_width, svg_height = self.svg_size

        x = (self.width() - svg_width) / 2
        y = (self.height() - svg_height) / 2
        target_rect = QRectF(x, y, svg_width, svg_height)

        self.renderer.render(painter, target_rect)
        self.label.setPixmap(pixmap)

        painter.end()

    def set_highlighted(self, highlighted: bool) -> None:
        self.renderer = self.renderer_alt \
            if highlighted else self.renderer_default

        self._update_pixmap()

    def resizeEvent(self, event):
        self._update_pixmap()
        super().resizeEvent(event)
