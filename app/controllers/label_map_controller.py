import json
from dataclasses import dataclass, asdict
from typing import TYPE_CHECKING

from app.exceptions.label_map import (
    InvalidJSONException,
    InvalidFormatException,
    InvalidIDsException,
    InvalidNamesException,
    LabelNotFoundException
)

if TYPE_CHECKING:
    from annotator import MainWindow


@dataclass
class LabelSchema:
    label_name: str
    kpt_names: list[str]
    kpt_edges: list[tuple[int, int]]
    kpt_symmetry: list[tuple[int, int]]

    def to_dict(self) -> dict:
        return asdict(self)


class LabelMapController:
    def __init__(self, parent: 'MainWindow') -> None:
        self.labels = parent.settings.get('label_map')
        self.parent = parent

        self._id_index, self._schema_index = {}, {}
        self._index_labels()

    def _index_labels(self) -> None:
        self._id_index, self._schema_index = {}, {}

        for label in self.labels:
            kpt_names = label.get('keypoints', [])
            kpt_edges = label.get('skeleton', [])
            kpt_symmetry = label.get('symmetry', [])

            self._id_index[label['name']] = label['id']
            self._schema_index[label['name']] = LabelSchema(
                label['name'], kpt_names, kpt_edges, kpt_symmetry)

    def load_labels(self, label_map_path: str) -> None:
        with open(label_map_path, 'r') as json_file:
            try:
                label_map = json.load(json_file)
            except json.JSONDecodeError:
                raise InvalidJSONException()

        try:
            names = [item['name'] for item in label_map]
            ids = [item['id'] for item in label_map]
        except (KeyError, TypeError):
            raise InvalidFormatException()

        if len(ids) != len(set(ids)) or \
                not all(isinstance(id_, int) and id_ >= 1 for id_ in ids):
            raise InvalidIDsException()

        if len(names) != len(set(names)) or \
                not all(isinstance(name, str) for name in names):
            raise InvalidNamesException()

        self.labels = label_map
        self._index_labels()

        self.parent.settings.set('label_map', label_map)
        self.parent.settings.set('hidden_categories', [])

        self.parent.settings_window.settings_manager.\
            setting_hidden_categories.hidden_categories.clear()

    def get_id(self, label_name: str) -> int:
        if label_name in self._id_index:
            return self._id_index[label_name]

        raise LabelNotFoundException()

    def get_label_schema(self, label_name: str) -> LabelSchema:
        if label_name in self._schema_index:
            return self._schema_index[label_name]

        raise LabelNotFoundException()

    def contains(self, label_name: str) -> bool:
        return label_name in self._id_index
