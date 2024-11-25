import hashlib

import enchant
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication

us_dict = enchant.Dict('en_US')


def setup_dark_theme(app: QApplication) -> None:
    palette = QPalette()

    dark_gray = QColor(33, 33, 33)
    light_gray = QColor(200, 200, 200)
    medium_gray_1 = QColor(53, 53, 53)
    medium_gray_2 = QColor(80, 80, 80)
    white = QColor(255, 255, 255)
    red = QColor(255, 0, 0)

    palette.setColor(QPalette.ColorRole.Window, dark_gray)
    palette.setColor(QPalette.ColorRole.WindowText, light_gray)
    palette.setColor(QPalette.ColorRole.Base, dark_gray)
    palette.setColor(QPalette.ColorRole.AlternateBase, medium_gray_1)
    palette.setColor(QPalette.ColorRole.ToolTipBase, light_gray)
    palette.setColor(QPalette.ColorRole.ToolTipText, light_gray)
    palette.setColor(QPalette.ColorRole.Text, light_gray)
    palette.setColor(QPalette.ColorRole.Button, dark_gray)
    palette.setColor(QPalette.ColorRole.ButtonText, light_gray)
    palette.setColor(QPalette.ColorRole.BrightText, red)
    palette.setColor(QPalette.ColorRole.Highlight, medium_gray_2)
    palette.setColor(QPalette.ColorRole.HighlightedText, white)

    app.setPalette(palette)


def text_to_color(text: str) -> tuple[int, int, int]:
    hash_code = int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16)

    red = hash_code % 255
    green = (hash_code // 255) % 255
    blue = (hash_code // 65025) % 255

    return red, green, blue


def pretty_text(text: str) -> str:
    words = text.replace('_', ' ').replace('-', ' ').split(' ')
    words = [word.capitalize() if us_dict.check(word) else word.upper()
             for word in words]

    return ' '.join(words)
