from typing import TYPE_CHECKING

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from annotator import MainWindow

__confirm_reset__ = 'Reset all settings to their default values?'

__confirm_import__ = ('You already have existing annotations in this session. '
                      'Are you sure you want to import a file?'
                      '\n\nThe imported annotations will be '
                      'added to your existing ones.')

__confirm_export__ = ('Your annotations will be automatically saved, but '
                      'have not been exported yet.\n\nExport before leaving?')

__import_fail__ = ('The contents of this file have already '
                   'been imported into this session.')


class MessageBox(QMessageBox):
    def __init__(self,
                 parent: 'MainWindow',
                 title: str,
                 message: str,
                 default: bool,
                 icon_path: str = None,
                 ) -> None:
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setText(message)

        self.setStandardButtons(QMessageBox.StandardButton.Yes
                                | QMessageBox.StandardButton.No)

        default_button = QMessageBox.StandardButton.Yes \
            if default else QMessageBox.StandardButton.No

        self.setDefaultButton(default_button)
        self.setIconPixmap(QIcon(icon_path).pixmap(96, 96))

    def exec(self) -> bool:
        return super().exec() == QMessageBox.StandardButton.Yes


class InformationBox(QMessageBox):
    def __init__(self, parent: 'MainWindow', title: str, text: str) -> None:
        super().__init__(parent)

        self.setIcon(QMessageBox.Icon.Information)
        self.setWindowTitle(title)
        self.setText(text)


class ConfirmResetSettingsBox(MessageBox):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent, 'Confirm Reset', __confirm_reset__, False)


class ConfirmImportBox(MessageBox):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent,
                         'Confirm Import',
                         __confirm_import__,
                         False,
                         'icon:import.png',)


class ConfirmExitBox(MessageBox):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent,
                         'Confirm Exit',
                         __confirm_export__,
                         True,
                         'icon:export.png',)


class ImportFailedBox(InformationBox):
    def __init__(self, parent: 'MainWindow') -> None:
        super().__init__(parent, 'Can\'t Import File', __import_fail__)
