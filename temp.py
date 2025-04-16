import sys
import random

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap, QPen, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsRectItem,
    QGraphicsItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent
)

EDGE_THICKNESS = 8
IMAGE_PATH = r'C:\Users\shkol\Downloads\hospital_images\patient room trending.png'

# How close new boxes can be to the original one (in pixels)
MIN_DISTANCE = 200


class Annotation(QGraphicsRectItem):
    def __init__(self, position: list[float]) -> None:
        super().__init__(*position)
        self.setPen(QPen(QColor(76, 207, 161), 2))

        self._hovered_edge = None
        self._resizing = False
        self._start_rect = QRectF()
        self._start_mouse = QPointF()
        self._last_hover_pos = QPointF()

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def boundingRect(self) -> QRectF:
        return self.rect().normalized().adjusted(
            -EDGE_THICKNESS, -EDGE_THICKNESS, EDGE_THICKNESS, EDGE_THICKNESS)

    def shape(self) -> QPainterPath:
        margin = EDGE_THICKNESS / 2
        rect = self.rect().adjusted(-margin, -margin, margin, margin)
        path = QPainterPath()
        path.addRect(rect)
        return path

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._last_hover_pos = event.pos()
        x, y = event.pos().x(), event.pos().y()
        r = self.rect()
        near_top = abs(y - r.top()) < EDGE_THICKNESS
        near_left = abs(x - r.left()) < EDGE_THICKNESS
        near_right = abs(x - r.right()) < EDGE_THICKNESS
        near_bottom = abs(y - r.bottom()) < EDGE_THICKNESS

        # decide hovered edge
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

        self.update()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered_edge = None
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._hovered_edge:
            self._resizing = True
            self._start_rect = self.rect()
            self._start_mouse = event.pos()
        else:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        # bring this annotation to front
        z_values = (item.zValue() for item in self.scene().items())
        self.setZValue(max(z_values) + 1)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._resizing:
            self._resize(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._resizing:
            self._resizing = False
            self.setRect(self.rect().normalized())
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def _resize(self, event: QGraphicsSceneMouseEvent) -> None:
        dx = event.pos().x() - self._start_mouse.x()
        dy = event.pos().y() - self._start_mouse.y()

        top_shift    = dy if 'top'    in self._hovered_edge else 0
        left_shift   = dx if 'left'   in self._hovered_edge else 0
        right_shift  = dx if 'right'  in self._hovered_edge else 0
        bottom_shift = dy if 'bottom' in self._hovered_edge else 0

        self.setRect(QRectF(self._start_rect).adjusted(
            left_shift, top_shift, right_shift, bottom_shift))

    def paint(self, painter: QPainter, option, widget=None) -> None:
        r = self.rect().normalized()
        t = EDGE_THICKNESS

        fills: list[QRectF] = []
        if self._hovered_edge:
            edges = self._hovered_edge.split('_') if '_' in self._hovered_edge else [self._hovered_edge]
            for e in edges:
                if e == 'left':
                    fills.append(QRectF(r.left(), r.top(), t, r.height()))
                elif e == 'right':
                    fills.append(QRectF(r.right() - t, r.top(), t, r.height()))
                elif e == 'top':
                    fills.append(QRectF(r.left(), r.top(), r.width(), t))
                elif e == 'bottom':
                    fills.append(QRectF(r.left(), r.bottom() - t, r.width(), t))
        else:
            if r.contains(self._last_hover_pos):
                fills.append(QRectF(r))

        if fills:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(76, 207, 161, 100))
            if len(fills) == 1:
                painter.drawRect(fills[0])
            else:
                path = QPainterPath()
                path.setFillRule(Qt.FillRule.WindingFill)
                for fr in fills:
                    path.addRect(fr)
                painter.drawPath(path)
            painter.restore()

        super().paint(painter, option, widget)

class CanvasView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene()
        pixmap = QPixmap(IMAGE_PATH)
        self.scene.addPixmap(pixmap)

        # original annotation
        original = Annotation([100, 100, 200, 150])
        self.scene.addItem(original)

        # generate 500 random boxes, not too close to original
        orig_center = original.rect().center()
        for _ in range(5000):
            # fixed size or random size
            w, h = 60, 40
            while True:
                x = random.uniform(0, 800 - w)
                y = random.uniform(0, 600 - h)
                # ensure distance > MIN_DISTANCE
                dx = (x + w/2) - orig_center.x()
                dy = (y + h/2) - orig_center.y()
                if (dx*dx + dy*dy) >= MIN_DISTANCE**2:
                    break
            self.scene.addItem(Annotation([x, y, w, h]))

        self.setScene(self.scene)
        self.setSceneRect(0, 0, 800, 600)
        self.setRenderHints(QPainter.RenderHint.Antialiasing)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setCentralWidget(CanvasView())
        self.resize(800, 600)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
