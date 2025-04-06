import math
import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QResizeEvent, QMouseEvent, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QSizePolicy,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QLabel
)

from app.enums.settings import Setting
from app.utils import pretty_text, text_to_color
from app.widgets.settings.components.widgets import (
    SettingButton,
    ScrollableArea
)
from app.widgets.labels import InteractiveLabel
from app.widgets.settings.components.layouts import TitleLayout, FooterLayout

if TYPE_CHECKING:
    from app.widgets.settings.settings_window import SettingsWindow

__basepath__ = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
__iconpath__ = os.path.join(__basepath__, 'resources', 'icons')

__smooth_transform__ = Qt.TransformationMode.SmoothTransformation


class CategoriesMenu(QVBoxLayout):
    def __init__(self, parent: 'SettingsWindow') -> None:
        super().__init__()
        self.parent = parent

        self.empty_banner = EmptyBanner()
        self.category_list = CategoriesList(self)
        self.hidden_categories_label = HiddenCategoriesLabel(self)

        footer_layout = QHBoxLayout()
        footer_layout.addWidget(self.hidden_categories_label)
        footer_layout.addLayout(FooterLayout(parent, submenu=True))

        self.addLayout(TitleLayout(parent, 'Hidden categories'))
        self.addSpacing(12)

        self.addWidget(self.empty_banner)
        self.addWidget(self.category_list)
        self.addLayout(footer_layout)


class EmptyBanner(QWidget):
    icon_name = 'robo_bear_sleeping.png'
    message = 'No categories loaded.\nUpload a label map to get started.'

    def __init__(self) -> None:
        super().__init__()

        pixmap = QPixmap(os.path.join(__iconpath__, self.icon_name)).scaled(
            228, 124, transformMode=__smooth_transform__)

        icon_label = QLabel()
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        message_label = QLabel(self.message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addStretch()
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        layout.addStretch()


class CategoriesList(ScrollableArea):
    NUM_COLUMNS = 2

    def __init__(self, parent: CategoriesMenu) -> None:
        super().__init__()
        self.parent = parent

        self.toolbar = CategoriesToolBar(self)
        self.setViewportMargins(0, self.toolbar.sizeHint().height(), 0, 0)

        items_widget = QWidget()
        items_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.items_layout = QGridLayout(items_widget)
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

    def rebuild_categories(self) -> None:
        settings_window = self.parent.parent
        category_names = settings_window.parent.canvas.label_names

        (self.parent.empty_banner.hide(), self.show()) if category_names \
            else (self.parent.empty_banner.show(), self.hide())

        for category_item in self.findChildren(CategoryItem):
            category_item.deleteLater()

        for name in category_names:
            self.items_layout.addWidget(CategoryItem(self, name))

        self.parent.hidden_categories_label.update()
        self.verticalScrollBar().setValue(0)
        self.toolbar.search_bar.setText('')

        # Update after `deleteLater` calls are processed
        QTimer.singleShot(0, self.toolbar.toggle_button.update)
        QTimer.singleShot(0, self.redraw_categories)

    def redraw_categories(self) -> None:
        category_items = self.findChildren(CategoryItem)
        search_text = self.toolbar.search_bar.text().lower()

        visible_items = [item for item in category_items
                         if search_text in item.query_name]

        for item in category_items:
            item.hide()

        for index, item in enumerate(visible_items):
            item.show()

            self.items_layout.addWidget(
                item, index // self.NUM_COLUMNS, index % self.NUM_COLUMNS)

    def filter_categories(self) -> None:
        self.verticalScrollBar().setValue(0)
        self.redraw_categories()

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

        layout.setContentsMargins(0, 0, 0, 13)
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

        self.parent.parent.hidden_categories_label.update()
        self.parent.toolbar.search_bar.clear()
        self.parent.save_categories()

        self.update()

    def update(self) -> None:
        category_items = self.parent.findChildren(CategoryItem)
        hide = all(item.checkbox.isChecked() for item in category_items)

        toggle, text = (False, 'Hide All') if hide \
            else (True, 'Show All')

        self.current_action = lambda: self._toggle_all(toggle)
        self.setText(text)


class CategoriesSearchBar(QLineEdit):
    def __init__(self):
        super().__init__()

        clear_icon = QPixmap(os.path.join(__iconpath__, 'clear.png')).scaled(
            12, 16, transformMode=Qt.TransformationMode.SmoothTransformation)

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
        y_pos = frame_size.center().y() - button_size.height() // 2 + 1

        self.clear_button.move(x_pos, y_pos)


class CategoryItem(QWidget):
    def __init__(self, parent: CategoriesList, category_name: str) -> None:
        super().__init__()
        self.parent = parent

        self.category_name = category_name
        self.query_name = pretty_text(category_name).lower()

        checked = category_name not in parent.hidden_categories
        self.visibility_label = QLabel('Visible' if checked else 'Hidden')

        self.checkbox = CategoryCheckBox(self, category_name)
        self.checkbox.stateChanged.connect(self._on_toggle)
        self.checkbox.setChecked(checked)

        self.checkbox.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 14, 0)

        layout.addWidget(self.checkbox)
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
        self.checkbox.toggle()

        self.parent.parent.hidden_categories_label.update()
        self.parent.toolbar.toggle_button.update()
        self.parent.save_categories()


class CategoryCheckBox(QCheckBox):
    def __init__(self, parent: CategoryItem, category_name: str) -> None:
        super().__init__(pretty_text(category_name))
        self.parent = parent

        self.setStyleSheet(f'''::indicator:checked {{
            background-color: rgb{text_to_color(category_name)};}}''')

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.parent.mouseReleaseEvent(event)


class HiddenCategoriesLabel(InteractiveLabel):
    def __init__(self, parent: CategoriesMenu) -> None:
        super().__init__()

        self.parent = parent
        self.setContentsMargins(6, 0, 0, 0)

    def _view_next_hidden(self) -> None:
        category_list = self.parent.category_list
        scroll_bar = category_list.verticalScrollBar()

        widgets = category_list.findChildren(CategoryItem)
        hidden_cats = category_list.hidden_categories

        start_index = next((
            index + 1 for index in range(len(widgets))
            if category_list.is_in_view(widgets[index])))

        num_columns = category_list.NUM_COLUMNS
        start_index = math.ceil(start_index / num_columns) * num_columns

        # Rotate widgets to start from top-most visible widget
        widgets = widgets[start_index:] + widgets[:start_index]
        widgets = filter(lambda w: w.category_name in hidden_cats, widgets)

        for widget in widgets:
            if category_list.can_scroll_to_widget(widget):
                category_list.scroll_to_widget(widget)
                break

            elif scroll_bar.value() < scroll_bar.maximum():
                category_list.scroll_to_value(scroll_bar.maximum())
                break

    def update(self) -> None:
        hidden_cats = self.parent.category_list.hidden_categories
        label_names = self.parent.parent.parent.canvas.label_names

        self.setVisible(bool(hidden_cats))
        self.clear()

        if hidden_cats == set(label_names):
            self.add_text('All categories hidden')
            return

        if len(hidden_cats) == 1:
            hypertext = pretty_text(next(iter(hidden_cats)))

        else:
            hypertext = f'{len(hidden_cats)} categories'

        self.add_hypertext(hypertext, self._view_next_hidden)
        self.add_text('hidden')

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()
