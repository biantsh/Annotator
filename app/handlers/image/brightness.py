from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap, QImage

from app.utils import clip_value

if TYPE_CHECKING:
    from app.canvas import Canvas


class BrightnessHandler:
    _min_steps = 0
    _max_steps = 20

    def __init__(self, parent: 'Canvas') -> None:
        self.parent = parent
        self.step = self._min_steps

        self._format = QImage.Format.Format_ARGB32
        self._array = None

        self._lookup_tables = []

        # Index possible gamma offset values for runtime efficiency
        for step in range(self._max_steps + 1):
            table = np.zeros(256, dtype=np.uint8)

            for index in range(256):
                table[index] = (index / 255) ** (1 - 0.03 * step) * 255

            self._lookup_tables.append(table)

        self.draw_indicator = False
        self.indicator_timer = QTimer()
        self.indicator_timer.timeout.connect(self.unset_indicator)

    def _array_to_pixmap(self, array: np.ndarray) -> QPixmap:
        data, strides = array.data, array.strides[0]
        height, width, _ = array.shape

        image = QImage(data, width, height, strides, self._format)
        return QPixmap.fromImage(image)

    def _set_brightness(self, step: int) -> None:
        self.step = clip_value(step, self._min_steps, self._max_steps)
        lookup_table = self._lookup_tables[self.step]

        array = self._array.copy()
        array[..., :3] = lookup_table[array[..., :3]]

        self.parent.pixmap = self._array_to_pixmap(array)
        self.set_indicator()

    def increase_brightness(self) -> None:
        self._set_brightness(self.step + 1)

    def decrease_brightness(self) -> None:
        self._set_brightness(self.step - 1)

    def toggle_brightness(self) -> None:
        if self.step == self._max_steps:
            self._set_brightness(self._min_steps)
        else:
            self._set_brightness(self._max_steps)

    def unset_indicator(self) -> None:
        self.draw_indicator = False
        self.parent.update()

    def set_indicator(self) -> None:
        self.draw_indicator = True
        self.indicator_timer.start(2000)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        image = pixmap.toImage().convertToFormat(self._format)
        width, height = image.width(), image.height()

        pointer = image.bits()
        pointer.setsize(image.bytesPerLine() * height)

        array = np.frombuffer(pointer, dtype=np.uint8)
        array = array.reshape((height, image.bytesPerLine()))
        array = array[:, :width * 4].reshape((height, width, 4))

        self._array = array.reshape(image.height(), image.width(), 4).copy()

    def reset(self) -> None:
        self.step = self._min_steps
        self.unset_indicator()
