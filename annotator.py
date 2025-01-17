import os
import traceback
import sys
from types import TracebackType
from typing import Type

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QPalette,
    QColor,
    QIcon,
    QCloseEvent,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QFileDialog
)

from app import __appname__, __version__
from app.actions import ToolBarActions
from app.canvas import Canvas
from app.controllers.annotation_controller import AnnotationController
from app.controllers.button_controller import ButtonController
from app.controllers.image_controller import ImageController
from app.controllers.label_map_controller import LabelMapController
from app.controllers.logging_controller import LoggingController
from app.exceptions.io import IOException, InvalidCOCOException
from app.exceptions.label_map import LabelMapException
from app.settings import Settings
from app.widgets.annotation_list import AnnotationList
from app.widgets.message_box import (
    ConfirmImportBox,
    ConfirmExitBox,
    ImportFailedBox,
    InformationBox
)
from app.widgets.settings_window import SettingsWindow
from app.widgets.toast import Toast
from app.screens.home_screen import HomeScreen
from app.screens.main_screen import MainScreen
from app.widgets.toolbar import ToolBar

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__stylepath__ = os.path.join(__basepath__, 'app', 'styles', 'app.qss')

__respath__ = os.path.join(__basepath__, 'resources')
__iconpath__ = os.path.join(__respath__, 'icons')

__homepath__ = os.path.join(__respath__, 'screens',  'home_screen.svg')
__homepath_alt__ = os.path.join(__respath__, 'screens', 'home_screen_alt.svg')

QtCore.QDir.addSearchPath('icon', __iconpath__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(1000, 600)

        self.settings = Settings()

        self.image_controller = ImageController()
        self.label_map_controller = LabelMapController(self)
        self.annotation_controller = AnnotationController(self)
        self.button_controller = ButtonController(self)
        self.logging_controller = LoggingController(self)

        self.toolbar_actions = ToolBarActions(self).actions
        self.toolbar = ToolBar(self.toolbar_actions)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbar)

        self.settings_window = SettingsWindow(self)

        self.canvas = Canvas(self)
        self.annotation_list = AnnotationList(self)

        self.home_screen = HomeScreen(__homepath__, __homepath_alt__)
        self.main_screen = MainScreen(self)

        self.screens = QStackedWidget()
        self.screens.addWidget(self.home_screen)
        self.screens.addWidget(self.main_screen)

        self.setCentralWidget(self.screens)
        self.screens.setCurrentWidget(self.home_screen)

        toast_message = 'Press Esc or F11 to exit full screen'
        self.full_screen_toast = Toast(self, toast_message)

    def reload(self) -> None:
        image_path = self.image_controller.get_image_path()
        image_name = self.image_controller.get_image_name()

        self.setWindowTitle(self.image_controller.get_image_status())
        self.canvas.load_image(image_path)

        anno_info = self.annotation_controller.load_annotations(image_name)
        self.canvas.load_annotations(anno_info['annotations'])
        self.annotation_list.redraw_widgets()

    def open_dir(self, dir_path: str) -> None:
        self.image_controller.load_images(dir_path)
        self.canvas.reset()

        if self.image_controller.image_paths:
            self.screens.setCurrentWidget(self.main_screen)
            self.reload()

        else:
            self.screens.setCurrentWidget(self.home_screen)
            self.setWindowTitle(f'{__appname__} {__version__}')

        self.button_controller.set_enabled_buttons()
        self.settings.set('default_image_dir', dir_path)

    def open_label_map(self, label_map_path: str) -> None:
        try:
            self.label_map_controller.load_labels(label_map_path)
            self.settings.set('default_label_path', label_map_path)
        except LabelMapException as error:
            InformationBox(self, 'Invalid Label Map', error.message).exec()
            return

        if self.image_controller.image_paths:
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

    def prompt_import(self) -> None:
        if self.annotation_controller.has_annotations():
            if not ConfirmImportBox(self).exec():
                return

        import_path_setting = 'default_import_path'
        path = self.settings.get(import_path_setting)

        title = 'Select Annotations File'
        ext = 'JSON Files (*.json)'

        if file_path := QFileDialog.getOpenFileName(self, title, path, ext)[0]:
            self.settings.set(import_path_setting, file_path)

            try:
                self.import_annotations(file_path)
            except InvalidCOCOException as error:
                InformationBox(self, 'Invalid File', error.message).exec()
                return

    def prompt_export(self) -> str | None:
        export_path_setting = 'default_export_path'

        path = self.settings.get(export_path_setting)
        title = 'Select Output File'
        ext = 'JSON Files (*.json)'

        if file_path := QFileDialog.getSaveFileName(self, title, path, ext)[0]:
            self.settings.set(export_path_setting, file_path)

            try:
                self.export_annotations(file_path)
            except IOException as error:
                InformationBox(self, 'Unable to Export', error.message).exec()
                return

        return file_path

    def import_annotations(self, annotations_path: str) -> None:
        if self.annotation_controller.import_annotations(annotations_path):
            image_name = self.image_controller.get_image_name()
            anno_info = self.annotation_controller.load_annotations(image_name)

            self.canvas.load_annotations(anno_info['annotations'])
            self.annotation_list.redraw_widgets()
        else:
            ImportFailedBox(self).exec()

    def export_annotations(self, output_path: str) -> None:
        self.canvas.save_progress()

        self.annotation_controller.export_annotations(output_path)
        self.reload()

    def open_settings(self) -> None:
        if self.settings_window.isVisible():
            self.settings_window.close()
        else:
            self.settings_window.show()

    def on_crash(self,
                 exception_type: Type[BaseException],
                 exception: BaseException,
                 stack_trace: TracebackType
                 ) -> None:
        self.logging_controller.log_crash(''.join(traceback.format_exception(
            exception_type, exception, stack_trace)))

        sys.__excepthook__(exception_type, exception, stack_trace)
        sys.exit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0]

            if os.path.isdir(file_path.toLocalFile()):
                event.acceptProposedAction()

                self.home_screen.set_highlighted(True)
                self.activateWindow()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self.home_screen.set_highlighted(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self.home_screen.set_highlighted(False)

        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0]

            if os.path.isdir(file_path.toLocalFile()):
                self.open_dir(file_path.toLocalFile())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.canvas.save_progress()

        if not self.annotation_controller.has_annotations():
            return

        if ConfirmExitBox(self).exec():
            if not self.prompt_export():
                event.ignore()


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
    app.setWindowIcon(QIcon('icon:annotator.png'))
    app.setApplicationName(f'{__appname__} {__version__}')

    setup_dark_theme(app)

    window = MainWindow()
    window.showMaximized()

    sys.excepthook = window.on_crash
    app.exec()
