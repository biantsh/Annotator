from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QWidget,
    QCheckBox,
    QLabel
)

from app.styles.style_sheets import CategoryCheckBoxStyleSheet
from app.utils import pretty_text, text_to_color
from app.widgets.settings.components.layouts import TitleLayout, FooterLayout

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow


class CategoriesMenu(QVBoxLayout):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()

        self.parent = parent
        self.category_list = CategoryList(parent)

        self.addLayout(TitleLayout(parent, 'Hidden categories'))
        self.addSpacing(10)

        self.addWidget(self.category_list)
        self.addLayout(FooterLayout(parent, submenu=True))

    def redraw(self) -> None:
        self.category_list.redraw()


class CategoryList(QScrollArea):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()
        self.parent = parent

        container_widget = QWidget()
        container_widget.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Maximum
        )

        self.setWidget(container_widget)
        self.setWidgetResizable(True)

        self.layout = QVBoxLayout(container_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

    def redraw(self) -> None:
        for index in reversed(range(self.layout.count())):
            self.layout.itemAt(index).widget().setParent(None)

        for category in self.parent.parent.canvas.label_names:
            self.layout.addWidget(CategoryItem(self.parent, category))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()


class CategoryItem(QWidget):
    def __init__(self, parent: 'SettingsWindow', category_name: str) -> None:
        super().__init__()

        self.parent = parent
        self.category_name = category_name

        self.checkbox = CategoryCheckBox(category_name)
        self.checkbox.setChecked(category_name not in self.hidden_categories)

        self.checkbox.stateChanged.connect(self.on_toggle)
        self.visibility_label = VisibilityLabel(self)

        layout = QHBoxLayout(self)
        self.setLayout(layout)

        layout.addWidget(self.checkbox)
        layout.addWidget(QLabel(category_name))
        layout.addStretch()
        layout.addWidget(self.visibility_label)

        layout.setContentsMargins(0, 0, 14, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    @property
    def hidden_categories(self) -> set[str]:
        return self.parent.settings_manager. \
            setting_hidden_categories.hidden_categories

    def on_toggle(self) -> None:
        self.hidden_categories.discard(self.category_name)

        if not self.checkbox.isChecked():
            self.hidden_categories.add(self.category_name)

        self.visibility_label.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()

            self.parent.parent.settings.set(
                'hidden_categories', list(self.hidden_categories))


class CategoryCheckBox(QCheckBox):
    def __init__(self, category_name: str) -> None:
        super().__init__(pretty_text(category_name))

        color = str(text_to_color(category_name))
        self.setStyleSheet(str(CategoryCheckBoxStyleSheet(color)))


class VisibilityLabel(QLabel):
    def __init__(self, parent: CategoryItem) -> None:
        super().__init__('Visible')

        self.parent = parent
        self.update()

    def update(self) -> None:
        checked = self.parent.checkbox.isChecked()
        self.setText('Visible' if checked else 'Hidden')
