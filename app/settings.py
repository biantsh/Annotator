import json
import os

from platformdirs import user_config_dir

from app import __appname__


class Settings:
    def __init__(self) -> None:
        app_dir = os.path.join(user_config_dir(), __appname__)
        os.makedirs(app_dir, exist_ok=True)

        self._settings_path = os.path.join(app_dir, 'settings.json')
        self._settings = {}

        if os.path.exists(self._settings_path):
            with open(self._settings_path, 'r') as json_file:
                self._settings = json.load(json_file)

    def _save(self) -> None:
        with open(self._settings_path, 'w') as json_file:
            json.dump(self._settings, json_file, indent=2)

    def get(self, setting: str) -> str:
        return self._settings.get(setting, '')

    def set(self, setting: str, value: str) -> None:
        self._settings[setting] = value
        self._save()
