import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShowEvent, QResizeEvent, QMouseEvent, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QLabel
)

from app.enums.settings import Setting
from app.styles.style_sheets import CategoryCheckBoxStyleSheet
from app.utils import pretty_text, text_to_color
from app.widgets.settings.components.widgets import (
    SettingButton,
    ScrollableArea
)
from app.widgets.settings.components.layouts import TitleLayout, FooterLayout

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')


class CategoriesMenu(QVBoxLayout):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()

        self.parent = parent
        self.category_list = CategoriesList(self)

        self.addLayout(TitleLayout(parent, 'Hidden categories'))
        self.addSpacing(10)

        self.addWidget(self.category_list)
        self.addLayout(FooterLayout(parent, submenu=True))


class CategoriesList(ScrollableArea):
    def __init__(self, parent: CategoriesMenu) -> None:
        super().__init__()
        self.parent = parent

        self.toolbar = CategoriesToolBar(self)
        self.setViewportMargins(0, self.toolbar.sizeHint().height(), 0, 0)

        items_widget = QWidget()
        items_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.items_layout = QVBoxLayout(items_widget)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(2)

        self.setWidget(items_widget)
        self.setWidgetResizable(True)

    @property
    def hidden_categories(self) -> set[str]:
        return self.parent.parent.settings_manager \
            .setting_hidden_categories.categories

    def save_categories(self) -> None:
        main_window = self.parent.parent.parent
        hidden_cats = self.hidden_categories

        main_window.settings.set(Setting.HIDDEN_CATEGORIES, list(hidden_cats))
        main_window.canvas.parent.annotation_list.redraw_widgets()
        main_window.canvas.update()

    def filter_categories(self) -> None:
        self.verticalScrollBar().setValue(0)
        query_text = self.toolbar.search_bar.text().lower()

        for category_item in self.findChildren(CategoryItem):
            category_name = category_item.category_name \
                .replace('_', ' ').replace('-', ' ')

            category_item.setVisible(query_text in category_name)

    def showEvent(self, event: QShowEvent) -> None:
        settings_window = self.parent.parent

        for index in reversed(range(self.items_layout.count())):
            self.items_layout.itemAt(index).widget().deleteLater()

        for label in settings_window.parent.canvas.label_names:
            self.items_layout.addWidget(CategoryItem(self, label))

        self.verticalScrollBar().setValue(0)
        self.toolbar.search_bar.setText('')

        # Update after `deleteLater` calls are processed
        QTimer.singleShot(0, self.toolbar.toggle_button.update)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.toolbar.setFixedWidth(self.viewport().width())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()


class CategoriesToolBar(QWidget):
    def __init__(self, parent: CategoriesList) -> None:
        super().__init__(parent)

        self.toggle_button = CategoriesToggleButton(parent)
        self.search_bar = CategoriesSearchBar()

        self.search_bar.setPlaceholderText('Search categories')
        self.search_bar.textChanged.connect(parent.filter_categories)

        layout = QHBoxLayout(self)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.search_bar)

        layout.setContentsMargins(0, 0, 0, 9)
        layout.setSpacing(3)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()


class CategoriesToggleButton(SettingButton):
    def __init__(self, parent: CategoriesList) -> None:
        super().__init__('Show All')
        self.parent = parent

        self.current_action = lambda: self._toggle_all(True)
        self.clicked.connect(lambda: self.current_action())

    def _toggle_all(self, checked: bool) -> None:
        category_list = self.parent.widget()

        for item in category_list.findChildren(CategoryItem):
            item.checkbox.setChecked(checked)

        self.parent.toolbar.search_bar.clear()
        self.parent.save_categories()

        self.update()

    def update(self) -> None:
        category_items = self.parent.widget().findChildren(CategoryItem)
        hide = all(item.checkbox.isChecked() for item in category_items)

        toggle, text = (False, 'Hide All') if hide \
            else (True, 'Show All')

        self.current_action = lambda: self._toggle_all(toggle)
        self.setText(text)


class CategoriesSearchBar(QLineEdit):
    def __init__(self):
        super().__init__()

        clear_icon_path = os.path.join(__iconpath__, 'clear.png')
        clear_icon = QPixmap(clear_icon_path).scaled(
            10, 14,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.clear_button = QPushButton(QIcon(clear_icon), '', self)
        self.clear_button.clicked.connect(self._on_clear)

    def _on_clear(self) -> None:
        self.setFocus()
        self.clear()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        button_size = self.clear_button.sizeHint()
        frame_size = self.contentsRect()

        x_pos = frame_size.right() - button_size.width()
        y_pos = frame_size.center().y() - button_size.height() // 2

        self.clear_button.move(x_pos, y_pos)


class CategoryItem(QWidget):
    def __init__(self, parent: CategoriesList, category_name: str) -> None:
        super().__init__()

        self.parent = parent
        self.category_name = category_name

        checked = category_name not in parent.hidden_categories
        self.visibility_label = QLabel('Visible' if checked else 'Hidden')

        self.checkbox = CategoryCheckBox(self, category_name)
        self.checkbox.stateChanged.connect(self._on_toggle)
        self.checkbox.setChecked(checked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 14, 0)

        layout.addWidget(self.checkbox)
        layout.addWidget(QLabel(category_name))
        layout.addStretch()
        layout.addWidget(self.visibility_label)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    def _on_toggle(self) -> None:
        hidden_cats = self.parent.hidden_categories

        self.visibility_label.setText('Hidden')
        hidden_cats.add(self.category_name)

        if self.checkbox.isChecked():
            self.visibility_label.setText('Visible')
            hidden_cats.discard(self.category_name)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()

            self.parent.toolbar.toggle_button.update()
            self.parent.save_categories()


class CategoryCheckBox(QCheckBox):
    def __init__(self, parent: CategoryItem, category_name: str) -> None:
        super().__init__(pretty_text(category_name))
        self.parent = parent

        color = str(text_to_color(category_name))
        self.setStyleSheet(str(CategoryCheckBoxStyleSheet(color)))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.parent.mouseReleaseEvent(event)
