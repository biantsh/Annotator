from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow

from app.actions import Actions
from app.canvas import Canvas
from app.image_manager import ImageManager
from app.toolbar import ToolBar

QtCore.QDir.addSearchPath('icon', 'resources/icons/')

__appname__ = 'Annotator'
__toolbar_area__ = Qt.ToolBarArea.LeftToolBarArea


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(800, 500)

        self.image_manager = ImageManager()

        self.actions = Actions(self).actions
        self.addToolBar(__toolbar_area__, ToolBar(self.actions))

        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)

    def open_dir(self, dir_path: str) -> None:
        self.image_manager.load_images(dir_path)

        app_title = __appname__
        nav_enabled = False

        if self.image_manager.num_images > 0:
            self.canvas.load_image(self.image_manager.get_image())

            app_title = self.image_manager.get_image_status()
            nav_enabled = True

        self.setWindowTitle(app_title)
        self.actions['next_image'].setEnabled(nav_enabled)
        self.actions['prev_image'].setEnabled(nav_enabled)

    def next_image(self) -> None:
        self.image_manager.next_image()

        self.setWindowTitle(self.image_manager.get_image_status())
        self.canvas.load_image(self.image_manager.get_image())

    def prev_image(self) -> None:
        self.image_manager.prev_image()

        self.setWindowTitle(self.image_manager.get_image_status())
        self.canvas.load_image(self.image_manager.get_image())


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle('fusion')
    app.setApplicationName(__appname__)
    app.setWindowIcon(QIcon('icon:annotator.png'))

    window = MainWindow()
    window.showMaximized()

    app.exec()
