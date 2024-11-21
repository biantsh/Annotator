from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow
)

import app.resources
from app.actions import Actions
from app.toolbar import ToolBar

__appname__ = 'labelImgPlus'


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        actions = Actions(self)

        toolbar = ToolBar(actions.actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)


if __name__ == '__main__':
    app = QApplication([])
    app.setApplicationName(__appname__)

    window = MainWindow()
    window.show()

    app.exec_()
