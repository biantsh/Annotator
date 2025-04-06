from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import (
    QMouseEvent,
    QPaintEvent,
    QCloseEvent,
    QShowEvent,
    QPainter,
    QColor
)
from PyQt6.QtWidgets import (
    QApplication,
    QStackedLayout,
    QWidget,
    QFrame,
    QDialog,
    QLineEdit
)

from app.enums.settings import SettingsLayout
from app.utils import clip_value
from app.widgets.settings.menus.categories_menu import CategoriesMenu
from app.widgets.settings.menus.settings_menu import SettingsMenu
from app.widgets.settings.settings_manager import SettingsManager

if TYPE_CHECKING:
    from annotator import MainWindow

__modality__ = Qt.WindowModality.NonModal
__background__ = Qt.WidgetAttribute.WA_TranslucentBackground
__windowtype__ = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool


class SettingsWindow(QDialog):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)

        self.parent = parent
        self.settings_manager = SettingsManager(self)

        self.setWindowModality(__modality__)
        self.setWindowFlags(__windowtype__)
        self.setAttribute(__background__)

        self.layouts = [QWidget(self) for _ in range(len(SettingsLayout))]
        self.layouts[SettingsLayout.MAIN].setLayout(SettingsMenu(self))
        self.layouts[SettingsLayout.CATEGORIES].setLayout(CategoriesMenu(self))

        self.layout = QStackedLayout()
        self.layout.addWidget(self.layouts[SettingsLayout.MAIN])
        self.layout.addWidget(self.layouts[SettingsLayout.CATEGORIES])

        self.popup = QFrame(self)
        self.popup.setLayout(self.layout)
        self.popup.setFixedSize(750, 500)

        self.dragging = False
        self.drag_offset = QPoint()

    def _set_actions_enabled(self, enabled: bool) -> None:
        canvas = self.parent.canvas
        main_window = self.parent

        for action in canvas.actions() + main_window.actions():
            if action.text() not in ('Settings', 'Escape'):
                action.setEnabled(enabled)

    def set_layout(self, layout: SettingsLayout) -> None:
        self.layout.setCurrentWidget(self.layouts[layout])

        if layout == SettingsLayout.CATEGORIES:
            categories_menu = self.layouts[layout].layout()

            categories_menu.category_list.toolbar.search_bar.setFocus()
            categories_menu.category_list.rebuild_categories()

    def show(self) -> None:
        self.layout.setCurrentWidget(self.layouts[SettingsLayout.MAIN])
        self.setGeometry(self.parent.frameGeometry())

        pos_x = (self.width() - self.popup.width()) // 2
        pos_y = (self.height() - self.popup.height()) // 2
        self.popup.move(pos_x, pos_y)

        super().showFullScreen() if self.parent.isFullScreen() \
            else super().showNormal()

        self.activateWindow()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        position = event.position().toPoint()
        global_position = event.globalPosition().toPoint()

        if not self.popup.geometry().contains(position):
            self.close()

        elif event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = global_position - self.popup.pos()
            self.dragging = True

            focused_widget = QApplication.focusWidget()
            if isinstance(focused_widget, QLineEdit):
                focused_widget.clearFocus()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.dragging:
            return

        new_pos = event.globalPosition().toPoint() - self.drag_offset
        x_pos, y_pos = new_pos.x(), new_pos.y()

        window = self.rect()
        popup = self.popup

        x_pos = clip_value(x_pos, 0, window.width() - popup.width())
        y_pos = clip_value(y_pos, 0, window.height() - popup.height())

        popup.move(x_pos, y_pos)

    def mouseReleaseEvent(self, _: QMouseEvent) -> None:
        self.dragging = False

    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        overlay_color = QColor(0, 0, 0, 150)
        painter.fillRect(self.rect(), overlay_color)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._set_actions_enabled(True)

    def showEvent(self, event: QShowEvent) -> None:
        self._set_actions_enabled(False)

        self.parent.canvas.set_selected_annotation(None)
        self.parent.canvas.set_selected_keypoint(None)
        self.parent.annotation_list.update()
