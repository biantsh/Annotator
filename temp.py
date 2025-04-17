# TODO:
#  1. Use an enum for hovered edges instead of a string, and simplify the
#   logic in hoverMoveEvent.
#  2. Instead of maintaining the self._hovered_edge attribute, create a
#   privtte function that calculates it when needed
#   (def self._get_hovered_state()?)

import sys

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap, QPen, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsRectItem,
    QGraphicsItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent,
    QStyleOptionGraphicsItem
)

MARGIN = 8
IMAGE_PATH = r'C:\Users\shkol\Downloads\hospital_images\patient room trending.png'


class AnnotationItem(QGraphicsRectItem):
    def __init__(self, position: list[float]) -> None:
        super().__init__(*position)

        self._hovered_edge = None
        self._is_hovered = False

        self.setAcceptHoverEvents(True)
        self.setPen(QPen(QColor(76, 207, 161), 2))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def _resize(self, event: QGraphicsSceneMouseEvent) -> None:
        shift = event.pos() - event.lastPos()

        top_shift = shift.y() if 'top' in self._hovered_edge else 0
        left_shift = shift.x() if 'left' in self._hovered_edge else 0
        right_shift = shift.x() if 'right' in self._hovered_edge else 0
        bottom_shift = shift.y() if 'bottom' in self._hovered_edge else 0

        self.setRect(self.rect().adjusted(
            left_shift, top_shift, right_shift, bottom_shift))

    def shape(self) -> QPainterPath:
        shape = self.boundingRect()

        path = QPainterPath()
        path.addRect(shape)

        return path

    def boundingRect(self) -> QRectF:
        return self.rect().normalized().adjusted(
            -MARGIN, -MARGIN, MARGIN, MARGIN)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        rect, mouse_pos = self.rect(), event.pos()

        near_top = abs(mouse_pos.y() - rect.top()) <= MARGIN
        near_left = abs(mouse_pos.x() - rect.left()) <= MARGIN
        near_right = abs(mouse_pos.x() - rect.right()) <= MARGIN
        near_bottom = abs(mouse_pos.y() - rect.bottom()) <= MARGIN

        if near_top and near_left:
            self._hovered_edge = 'top_left'
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)

        elif near_top and near_right:
            self._hovered_edge = 'top_right'
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)

        elif near_bottom and near_left:
            self._hovered_edge = 'bottom_left'
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)

        elif near_bottom and near_right:
            self._hovered_edge = 'bottom_right'
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)

        elif near_top:
            self._hovered_edge = 'top'
            self.setCursor(Qt.CursorShape.SizeVerCursor)

        elif near_bottom:
            self._hovered_edge = 'bottom'
            self.setCursor(Qt.CursorShape.SizeVerCursor)

        elif near_left:
            self._hovered_edge = 'left'
            self.setCursor(Qt.CursorShape.SizeHorCursor)

        elif near_right:
            self._hovered_edge = 'right'
            self.setCursor(Qt.CursorShape.SizeHorCursor)

        else:
            self._hovered_edge = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

        self._is_hovered = True
        self.update()

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered_edge = None
        self._is_hovered = False
        self.update()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if not self._hovered_edge:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        z_values = (item.zValue() for item in self.scene().items())
        self.setZValue(max(z_values) + 1)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._hovered_edge and event.buttons() & Qt.MouseButton.LeftButton:
            self._resize(event)

        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.setRect(self.rect().normalized())
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        super().mouseReleaseEvent(event)

    def paint(self,
              painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget = None
              ) -> None:
        hovered_edge = self._hovered_edge or ''
        rect = self.rect()

        fill_path = QPainterPath()
        fill_path.setFillRule(Qt.FillRule.WindingFill)

        if 'left' in hovered_edge:
            fill_path.addRect(rect.adjusted(0, 0, MARGIN - rect.width(), 0))

        if 'top' in hovered_edge:
            fill_path.addRect(rect.adjusted(0, 0, 0, MARGIN - rect.height()))

        if 'right' in hovered_edge:
            fill_path.addRect(rect.adjusted(rect.width() - MARGIN, 0, 0, 0))

        if 'bottom' in hovered_edge:
            fill_path.addRect(rect.adjusted(0, rect.height() - MARGIN, 0, 0))

        if self._is_hovered and not hovered_edge:
            fill_path.addRect(rect)

        painter.setBrush(QColor(76, 207, 161, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(fill_path)

        super().paint(painter, option, widget)


class CanvasView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()

        self.scene = QGraphicsScene()
        self.scene.addPixmap(QPixmap(IMAGE_PATH))
        self.scene.addItem(AnnotationItem([100, 100, 200, 150]))

        self.setScene(self.scene)
        self.setSceneRect(self.scene.sceneRect())
        self.setRenderHints(QPainter.RenderHint.Antialiasing)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setCentralWidget(CanvasView())


if __name__ == '__main__':
    app = QApplication([])
    win = MainWindow()
    win.show()

    sys.exit(app.exec())
