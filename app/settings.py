import json
import os
from typing import Any

from platformdirs import user_config_dir

from app import __appname__


class Settings:
    def __init__(self) -> None:
        app_dir = os.path.join(user_config_dir(), __appname__)
        os.makedirs(app_dir, exist_ok=True)

        self._settings_path = os.path.join(app_dir, 'settings.json')
        self._settings = {
            'label_map': [],
            'default_image_dir': '',
            'default_label_path': '',
            'default_import_path': '',
            'default_export_path': '',
            'add_missing_bboxes': False
        }

        if os.path.exists(self._settings_path):
            with open(self._settings_path, 'r') as json_file:
                self._settings.update(json.load(json_file))

    def _save(self) -> None:
        with open(self._settings_path, 'w') as json_file:
            json.dump(self._settings, json_file, indent=2)

    def get(self, setting: str) -> str:
        return self._settings[setting]

    def set(self, setting: str, value: Any) -> None:
        self._settings[setting] = value
        self._save()
