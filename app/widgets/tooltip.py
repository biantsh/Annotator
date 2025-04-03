from PyQt6.QtCore import Qt, QEvent, QObject, QTimer, QPoint
from PyQt6.QtGui import QCursor, QPainter, QBrush, QColor
from PyQt6.QtWidgets import QWidget, QLabel

__window_type__ = (Qt.WindowType.WindowTransparentForInput |
                   Qt.WindowType.FramelessWindowHint |
                   Qt.WindowType.Tool)


class Tooltip(QLabel):
    def __init__(self, parent: QWidget, delay: int, text: str = '') -> None:
        super().__init__(text)

        self.parent = parent
        parent.installEventFilter(self)

        self.background_color = QColor(20, 20, 20, 154)
        self.border_radius = 4

        self._timer = QTimer(self, interval=delay, singleShot=True)
        self._timer.timeout.connect(self.show)
        self._enabled = True

        self.setWindowFlags(__window_type__)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def disable(self) -> None:
        self._enabled = False
        self._timer.stop()

    def enable(self) -> None:
        self._enabled = True

    def show(self) -> None:
        self.adjustSize()

        offset = QPoint(self.width(), self.height())
        self.move(QCursor.pos() - offset)

        super().show()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(Qt.PenStyle.NoPen)

        painter.drawRoundedRect(self.rect(),
                                self.border_radius,
                                self.border_radius)

        super().paintEvent(event)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if not self._enabled:
            return False

        if event.type() == QEvent.Type.Enter:
            self._timer.start()

        if event.type() in (QEvent.Type.MouseButtonPress,
                            QEvent.Type.Leave):
            self._timer.stop()
            self.hide()

        return False
