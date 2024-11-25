from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow

from app import __appname__
from app.actions import ToolBarActions
from app.canvas import Canvas
from app.controllers.annotation_controller import AnnotationController
from app.controllers.button_controller import ButtonController
from app.controllers.image_controller import ImageController
from app.controllers.label_map_controller import LabelMapController
from app.settings import Settings
from app.utils import setup_dark_theme
from app.widgets.toolbar import ToolBar

__toolbar_area__ = Qt.ToolBarArea.LeftToolBarArea
QtCore.QDir.addSearchPath('icon', 'resources/icons/')


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(800, 500)

        self.settings = Settings()

        self.image_controller = ImageController()
        self.label_map_controller = LabelMapController()
        self.annotation_controller = AnnotationController()
        self.button_controller = ButtonController(self)

        self.toolbar_actions = ToolBarActions(self).actions
        self.addToolBar(__toolbar_area__, ToolBar(self.toolbar_actions))

        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)

    def _on_image_change(self) -> None:
        """Called when navigating to a new image."""
        self.setWindowTitle(self.image_controller.get_image_status())

        image_path = self.image_controller.get_image_path()
        image_name = self.image_controller.get_image_name()
        annotations = self.annotation_controller.get_annotations(image_name)

        self.canvas.load_image(image_path)
        self.canvas.load_annotations(annotations)

    def open_dir(self, dir_path: str) -> None:
        self.image_controller.load_images(dir_path)
        self.canvas.reset()

        self.setWindowTitle(__appname__)
        if self.image_controller.num_images > 0:
            self._on_image_change()

        self.button_controller.set_enabled_buttons()

    def open_label_map(self, label_map_path: str) -> None:
        self.label_map_controller.load_labels(label_map_path)
        self.annotation_controller.labels = self.label_map_controller.labels

        self.button_controller.set_enabled_buttons()

    def next_image(self) -> None:
        self.image_controller.next_image()
        self._on_image_change()

    def prev_image(self) -> None:
        self.image_controller.prev_image()
        self._on_image_change()

    def import_annotations(self, annotations_path: str) -> None:
        self.annotation_controller.import_annotations(annotations_path)
        self._on_image_change()

    def export_annotations(self, output_path: str) -> None:
        self.annotation_controller.export_annotations(output_path)


if __name__ == '__main__':
    app = QApplication([__appname__])
    app.setWindowIcon(QIcon('icon:annotator.png'))

    setup_dark_theme(app)

    window = MainWindow()
    window.showMaximized()

    app.exec()
