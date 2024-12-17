from typing import TYPE_CHECKING

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from annotator import MainWindow

__confirm_import__ = ('You already have existing annotations in this session. '
                      'Are you sure you want to import a file?'
                      '\n\nThe imported annotations will be '
                      'added to your existing ones.')

__import_fail__ = ('The contents of this file have already '
                   'been imported into this session.')

__confirm_export__ = ('Your annotations will be automatically saved, but '
                      'have not been exported yet.\n\nExport before leaving?')


class MessageBox(QMessageBox):
    def __init__(self,
                 parent: 'MainWindow',
                 title: str,
                 icon_path: str,
                 message: str,
                 default: bool
                 ) -> None:
        super().__init__(parent)

        self.setIconPixmap(QIcon(icon_path).pixmap(96, 96))
        self.setWindowTitle(title)
        self.setText(message)

        self.setStandardButtons(QMessageBox.StandardButton.Yes
                                | QMessageBox.StandardButton.No)

        default_button = QMessageBox.StandardButton.Yes \
            if default else QMessageBox.StandardButton.No

        self.setDefaultButton(default_button)

    def exec(self) -> bool:
        return super().exec() == QMessageBox.StandardButton.Yes


class ConfirmImportBox(MessageBox):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent,
                         'Confirm Import',
                         'icon:import.png',
                         __confirm_import__,
                         False)


class ConfirmExitBox(MessageBox):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent,
                         'Confirm Exit',
                         'icon:export.png',
                         __confirm_export__,
                         True)


class ImportFailedBox(QMessageBox):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent)
        self.setIcon(QMessageBox.Icon.Information)

        self.setWindowTitle('Can\'t Import File')
        self.setText(__import_fail__)
