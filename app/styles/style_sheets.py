import os
import sys
from abc import ABC

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')


class StyleSheet(ABC):
    def __init__(self) -> None:
        self.style_sheet = ''

    def __str__(self) -> str:
        return self.style_sheet


class WidgetStyleSheet(StyleSheet):
    def __init__(self, background_color: str) -> None:
        super().__init__()

        self.style_sheet = f"""
            background-color: {background_color};
        """


class LabelStyleSheet(StyleSheet):
    def __init__(self, risky: bool) -> None:
        super().__init__()

        self.style_sheet = f"""
            color: {'red' if risky else 'white'};
            font-weight: {'bold' if risky else 'normal'};
        """


class CheckBoxStyleSheet(StyleSheet):
    def __init__(self,
                 selected: bool,
                 checkbox_color: tuple[int, int, int]
                 ) -> None:
        super().__init__()

        underline = '1px solid rgba(255, 255, 255, 0.85)' \
            if selected else '1px solid transparent'

        self.style_sheet = f"""
            QCheckBox {{
                background-color: transparent;
                font-weight: bold;
                margin-right: 24px;
                border-bottom: {underline};
            }}

            ::indicator {{
                border: 1px solid rgb(53, 53, 53);
                border-radius: 2px;
            }}

            ::indicator:checked {{
                background-color: rgb{checkbox_color};
            }}
        """


class SettingCheckBoxStyleSheet(StyleSheet):
    def __init__(self, hovered: bool, selected: bool) -> None:
        super().__init__()

        image_url = os.path.join(__iconpath__, 'checkbox.png')
        image_url = f'url({image_url})' if selected else 'none'
        outline = (60, 120, 216) if hovered or selected else (53, 53, 53)

        self.style_sheet = f"""
            ::indicator {{
                image: {image_url};
                border: 1px solid rgb{outline};
            }}
        """
