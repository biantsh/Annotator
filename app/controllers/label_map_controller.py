import json
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


class LabelMapController:
    def __init__(self, parent: 'MainWindow') -> None:
        self.labels = parent.settings.get('label_map')
        self.parent = parent

        self._id_index, self._kpt_index, self._sym_index = {}, {}, {}
        self._index_labels()

    def _index_labels(self) -> None:
        self._id_index, self._kpt_index, self._sym_index = {}, {}, {}

        for label in self.labels:
            self._id_index[label['name']] = label['id']
            self._kpt_index[label['name']] = label.get('skeleton', [])
            self._sym_index[label['name']] = label.get('symmetry', [])

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

    def get_id(self, label_name: str) -> int:
        if label_name in self._id_index:
            return self._id_index[label_name]

        raise LabelNotFoundException()

    def get_keypoint_info(self, label_name: str) -> list[int, int]:
        if label_name in self._kpt_index:
            return self._kpt_index[label_name]

        raise LabelNotFoundException()

    def get_symmetry_info(self, label_name: str) -> list[int, int]:
        if label_name in self._sym_index:
            return self._sym_index[label_name]

        raise LabelNotFoundException
