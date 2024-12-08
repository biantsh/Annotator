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
                border-bottom: {underline};
                margin-right: 10px;
                padding-bottom: 3px
            }}
        
            ::indicator {{
                border: 1px solid rgb(53, 53, 53);
                border-radius: 2px;
            }}
            
            ::indicator:checked {{
                background-color: rgb{checkbox_color};
            }}
        """
