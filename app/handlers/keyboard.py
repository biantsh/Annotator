from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent

if TYPE_CHECKING:
    from app.canvas import Canvas


class KeyboardHandler:
    def __init__(self, parent: 'Canvas') -> None:
        self.parent = parent

        self.pressed_keys = set()
        self.key_autorepeat_timer = QTimer()
        self.key_autorepeat_delay = QTimer()

        self.key_autorepeat_timer.setInterval(30)
        self.key_autorepeat_delay.setInterval(550)
        self.key_autorepeat_delay.setSingleShot(True)

        self.key_autorepeat_timer.timeout.connect(self._key_auto_repeat)
        self.key_autorepeat_delay.timeout.connect(
            self.key_autorepeat_timer.start)

    def _key_auto_repeat(self) -> None:
        self.parent.move_annotation_arrow(self.pressed_keys)

        if not self.pressed_keys:
            self.key_autorepeat_timer.stop()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat() or event.key() not in (
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right
        ):
            return

        self.pressed_keys.add(event.key())
        self.parent.move_annotation_arrow(self.pressed_keys)

        if not self.key_autorepeat_timer.isActive():
            self.key_autorepeat_delay.start()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return

        self.pressed_keys.discard(event.key())

        if not self.pressed_keys:
            self.key_autorepeat_timer.stop()
