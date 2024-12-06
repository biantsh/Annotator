import os
import sys

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPalette, QColor, QCloseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow

from app import __appname__
from app.actions import ToolBarActions
from app.canvas import Canvas
from app.controllers.annotation_controller import AnnotationController
from app.controllers.button_controller import ButtonController
from app.controllers.image_controller import ImageController
from app.controllers.label_map_controller import LabelMapController
from app.settings import Settings
from app.widgets.toolbar import ToolBar

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__stylepath__ = os.path.join(__basepath__, 'app', 'styles', 'app.qss')

__respath__ = os.path.join(__basepath__, 'resources')
__iconpath__ = os.path.join(__respath__, 'icons')
__screenpath__ = os.path.join(__respath__, 'screens')
__homepath__ = os.path.join(__screenpath__, 'home_screen.png')

QtCore.QDir.addSearchPath('icon', __iconpath__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(800, 500)

        self.settings = Settings()

        self.image_controller = ImageController()
        self.label_map_controller = LabelMapController()
        self.annotation_controller = AnnotationController(self)
        self.button_controller = ButtonController(self)

        self.toolbar_actions = ToolBarActions(self).actions
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea,
                        ToolBar(self.toolbar_actions))

        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)

        self.canvas.load_image(__homepath__)

    def reload(self) -> None:
        if not self.image_controller.image_paths:
            self.canvas.load_image(__homepath__)
            return

        image_path = self.image_controller.get_image_path()
        image_name = self.image_controller.get_image_name()

        self.canvas.save_progress()
        self.canvas.load_image(image_path)
        self.setWindowTitle(self.image_controller.get_image_status())

        if not self.label_map_controller.labels:
            return

        anno_info = self.annotation_controller.load_annotations(image_name)
        self.canvas.load_annotations(anno_info['annotations'])

    def open_dir(self, dir_path: str) -> None:
        self.image_controller.load_images(dir_path)
        self.canvas.reset()

        self.setWindowTitle(__appname__)

        self.button_controller.set_enabled_buttons()
        self.reload()

    def open_label_map(self, label_map_path: str) -> None:
        self.label_map_controller.load_labels(label_map_path)

        self.annotation_controller.labels = self.label_map_controller.labels
        self.canvas.labels = self.label_map_controller.labels

        self.button_controller.set_enabled_buttons()
        self.reload()

    def next_image(self) -> None:
        self.image_controller.next_image()
        self.reload()

    def prev_image(self) -> None:
        self.image_controller.prev_image()
        self.reload()

    def go_to_image(self, index: int) -> None:
        self.image_controller.go_to_image(index)
        self.reload()

    def import_annotations(self, annotations_path: str) -> None:
        self.annotation_controller.import_annotations(annotations_path)
        self.reload()

    def export_annotations(self, output_path: str) -> None:
        self.annotation_controller.export_annotations(output_path)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.canvas.save_progress()


def setup_dark_theme(application: QApplication) -> None:
    dark_gray = QColor(33, 33, 33)
    light_gray = QColor(200, 200, 200)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Base, dark_gray)
    palette.setColor(QPalette.ColorRole.Text, light_gray)
    palette.setColor(QPalette.ColorRole.Window, dark_gray)
    palette.setColor(QPalette.ColorRole.WindowText, light_gray)
    palette.setColor(QPalette.ColorRole.Button, dark_gray)
    palette.setColor(QPalette.ColorRole.ButtonText, light_gray)

    application.setPalette(palette)

    with open(__stylepath__, 'r') as qss_file:
        application.setStyleSheet(qss_file.read())


if __name__ == '__main__':
    app = QApplication([__appname__])
    app.setApplicationName(__appname__)
    app.setWindowIcon(QIcon('icon:annotator.png'))

    setup_dark_theme(app)

    window = MainWindow()
    window.showMaximized()

    app.exec()
