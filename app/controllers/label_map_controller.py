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
        self.parent.settings.set('label_map', label_map)

    def get_id(self, label_name: str) -> int:
        for item in self.labels:
            if item['name'] == label_name:
                return item['id']

        raise LabelNotFoundException()
