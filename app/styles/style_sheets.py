from abc import ABC


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
            min-width: 80
        """


class LabelStyleSheet(StyleSheet):
    def __init__(self, risky: bool) -> None:
        super().__init__()

        self.style_sheet = f"""
            color: {'red' if risky else 'white'};
            font-weight: {'bold' if risky else 'normal'};
        """


class CheckBoxStyleSheet(StyleSheet):
    def __init__(self, checkbox_color: tuple[int, int, int]) -> None:
        super().__init__()

        self.style_sheet = f"""
            QCheckBox {{
                font-weight: bold;
            }}
        
            ::indicator {{
                border: 1px solid gray;
                border-radius: 2px;
            }}
            
            ::indicator:checked {{
                background-color: rgb{checkbox_color};
            }}
        """
