import os
import sys
from abc import ABC

from app.objects import Annotation
from app.utils import text_to_color

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')


class StyleSheet(ABC):
    def __init__(self) -> None:
        self.style_sheet = ''

    def __str__(self) -> str:
        return self.style_sheet


class LabelStyleSheet(StyleSheet):
    def __init__(self, risky: bool) -> None:
        super().__init__()

        self.style_sheet = f"""
            color: {'red' if risky else 'white'};
            font-weight: {'bold' if risky else 'normal'};
        """


class CheckBoxStyleSheet(StyleSheet):
    def __init__(self, annotation: Annotation) -> None:
        super().__init__()

        anno_color = text_to_color(annotation.label_name)

        text_color, anno_color = ((200, 200, 200), (*anno_color, 1)) \
            if annotation.visible else ((117, 117, 117), (*anno_color, 0.5))

        underline = 'rgba(255, 255, 255, 0.85)' \
            if annotation.selected else 'transparent'

        self.style_sheet = f"""
            QCheckBox {{
                color: rgb{text_color};
                border-bottom: 1px solid {underline};
                background-color: transparent;
                font-weight: bold;
                margin-right: 24px;
                padding: 2px 0px;
            }}

            ::indicator {{
                background-color: rgba{anno_color};
                border-radius: 1px;
                margin-top: 1px;
                height: 14px;
                width: 2px;
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


class CategoryCheckBoxStyleSheet(StyleSheet):
    def __init__(self, color: str) -> None:
        super().__init__()

        self.style_sheet = f"""
            QCheckBox {{
                min-height: 48px;
                font-weight: bold;
                padding-left: 12px;
            }}

            ::indicator {{
                border: 1px solid rgb(53, 53, 53);
                border-radius: 3px;
            }}

            ::indicator:checked {{
                background-color: rgb{color};
            }}
        """
