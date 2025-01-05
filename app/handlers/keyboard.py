from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent

if TYPE_CHECKING:
    from app.canvas import Canvas


class KeyboardHandler:
    def __init__(self, parent: 'Canvas') -> None:
        self.parent = parent

        self.typed_number = ''
        self.pressed_keys = set()

        self.number_reset = QTimer()
        self.number_reset.setInterval(1000)
        self.number_reset.setSingleShot(True)
        self.number_reset.timeout.connect(self._reset_number)

        self.key_autorepeat_timer = QTimer()
        self.key_autorepeat_timer.setInterval(30)
        self.key_autorepeat_timer.timeout.connect(self._key_auto_repeat)

        self.key_autorepeat_delay = QTimer()
        self.key_autorepeat_delay.setInterval(550)
        self.key_autorepeat_delay.setSingleShot(True)
        self.key_autorepeat_delay.timeout.connect(
            self.key_autorepeat_timer.start)

    def _reset_number(self) -> None:
        self.typed_number = ''

    def _key_auto_repeat(self) -> None:
        self.parent.on_arrow_press(self.pressed_keys)

        if not self.pressed_keys:
            self.key_autorepeat_timer.stop()

    def on_number_press(self, event: QKeyEvent) -> None:
        self.typed_number += event.text()

        self.number_reset.stop()
        self.number_reset.start()

        self.parent.parent.go_to_image(int(self.typed_number))

    def on_arrow_press(self, event: QKeyEvent) -> None:
        self.pressed_keys.add(event.key())
        self.parent.on_arrow_press(self.pressed_keys)

        if not self.key_autorepeat_timer.isActive():
            self.key_autorepeat_delay.start()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.parent.keypoint_annotator.active:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Escape):
                self.parent.keypoint_annotator.end()

            elif event.key() == Qt.Key.Key_Space:
                self.parent.keypoint_annotator.reset_label()

            return

        if event.text().isdigit():
            self.on_number_press(event)

        elif not event.isAutoRepeat() and event.key() in (
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right
        ):
            self.on_arrow_press(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return

        self.pressed_keys.discard(event.key())

        if not self.pressed_keys:
            self.key_autorepeat_timer.stop()
