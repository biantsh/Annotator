import qdarktheme
from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow

from app.actions import Actions
from app.canvas import Canvas
from app.controllers.annotation_controller import AnnotationController
from app.controllers.button_controller import ButtonController
from app.controllers.image_controller import ImageController
from app.controllers.label_map_controller import LabelMapController
from app.toolbar import ToolBar

QtCore.QDir.addSearchPath('icon', 'resources/icons/')

__appname__ = 'Annotator'
__toolbar_area__ = Qt.ToolBarArea.LeftToolBarArea


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(800, 500)

        self.image_controller = ImageController()
        self.label_map_controller = LabelMapController()
        self.annotation_controller = AnnotationController()
        self.button_controller = ButtonController(self)

        self.actions = Actions(self).actions
        self.addToolBar(__toolbar_area__, ToolBar(self.actions))

        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)

    def open_dir(self, dir_path: str) -> None:
        self.image_controller.load_images(dir_path)
        self.canvas.reset()

        app_title = __appname__

        if self.image_controller.num_images > 0:
            app_title = self.image_controller.get_image_status()
            self.canvas.load_image(self.image_controller.get_image())

        self.setWindowTitle(app_title)
        self.button_controller.set_enabled_buttons()

    def open_label_map(self, label_map_path: str) -> None:
        self.label_map_controller.load_labels(label_map_path)
        self.annotation_controller.labels = self.label_map_controller.labels

        self.button_controller.set_enabled_buttons()

    def next_image(self) -> None:
        self.image_controller.next_image()

        self.setWindowTitle(self.image_controller.get_image_status())
        self.canvas.load_image(self.image_controller.get_image())

    def prev_image(self) -> None:
        self.image_controller.prev_image()

        self.setWindowTitle(self.image_controller.get_image_status())
        self.canvas.load_image(self.image_controller.get_image())

    def import_annotations(self, annotations_path: str) -> None:
        self.annotation_controller.import_annotations(annotations_path)

    def export_annotations(self, output_path: str) -> None:
        self.annotation_controller.export_annotations(output_path)


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle('fusion')
    app.setApplicationName(__appname__)
    app.setWindowIcon(QIcon('icon:annotator.png'))

    qdarktheme.setup_theme()

    window = MainWindow()
    window.showMaximized()

    app.exec()
