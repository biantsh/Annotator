from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox


class ExitMessageBox(QMessageBox):
    def __init__(self) -> None:
        super().__init__()

        self.setText("Your annotations will be automatically saved, "
                     "but have not been exported yet.\n\nExport "
                     "before leaving?")

        self.setIconPixmap(QIcon('icon:export.png').pixmap(96, 96))
        self.setStandardButtons(QMessageBox.StandardButton.Yes |
                                QMessageBox.StandardButton.No)

        self.setWindowTitle('Confirmation')
        self.setDefaultButton(QMessageBox.StandardButton.Yes)

    def exec(self) -> bool:
        return super().exec() == QMessageBox.StandardButton.Yes
