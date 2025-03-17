import json
import os
from typing import Any

from platformdirs import user_config_dir

from app import __appname__
from app.enums.settings import Setting


class Settings:
    def __init__(self) -> None:
        app_dir = os.path.join(user_config_dir(), __appname__)
        os.makedirs(app_dir, exist_ok=True)

        self._settings_path = os.path.join(app_dir, 'settings.json')
        self._settings = {
            Setting.LABEL_MAP: [],
            Setting.DEFAULT_IMAGE_DIR: '',
            Setting.DEFAULT_LABEL_PATH: '',
            Setting.DEFAULT_IMPORT_PATH: '',
            Setting.DEFAULT_EXPORT_PATH: '',
            Setting.HIDE_KEYPOINTS: False,
            Setting.HIDDEN_CATEGORIES: [],
            Setting.ADD_MISSING_BBOXES: False
        }

        if os.path.exists(self._settings_path):
            with open(self._settings_path, 'r') as json_file:
                self._settings.update(json.load(json_file))

    def _save(self) -> None:
        with open(self._settings_path, 'w') as json_file:
            json.dump(self._settings, json_file, indent=2)

    def get(self, setting_id: Setting) -> str:
        return self._settings[setting_id]

    def set(self, setting_id: Setting, value: Any) -> None:
        self._settings[setting_id] = value
        self._save()
