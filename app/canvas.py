from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QImageReader, QPixmap, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from annotator import MainWindow

__antialiasing__ = QPainter.RenderHint.Antialiasing
__pixmap_transform__ = QPainter.RenderHint.SmoothPixmapTransform


class Canvas(QWidget):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.pixmap = QPixmap()

    def _get_max_scale(self) -> float:
        if self.pixmap.isNull():
            return 1.0

        canvas = super().size()
        image = self.pixmap

        canvas_aspect = canvas.width() / canvas.height()
        image_aspect = image.width() / image.height()

        if canvas_aspect < image_aspect:
            return canvas.width() / image.width()

        return canvas.height() / image.height()

    def _get_center_offset(self) -> tuple[int, int]:
        canvas = super().size()
        image = self.pixmap

        scale = self._get_max_scale()
        offset_x = (canvas.width() - image.width() * scale) / 2
        offset_y = (canvas.height() - image.height() * scale) / 2

        return int(offset_x), int(offset_y)

    def reset(self) -> None:
        self.pixmap = QPixmap()
        self.update()

    def load_image(self, image_path: str) -> None:
        image = QImageReader(image_path).read()
        self.pixmap = QPixmap.fromImage(image)

        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Override, called when canvas is updated."""
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHints(__antialiasing__ | __pixmap_transform__)

        painter.translate(QPoint(*self._get_center_offset()))
        painter.scale(*[self._get_max_scale()] * 2)

        painter.drawPixmap(0, 0, self.pixmap)
