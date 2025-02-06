import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app import __appname__
from platformdirs import user_config_dir

if TYPE_CHECKING:
    from annotator import MainWindow


class LoggingController:
    def __init__(self, parent: 'MainWindow') -> None:
        self.parent = parent
        self.log_dir = os.path.join(user_config_dir(), __appname__, 'logs')

    @staticmethod
    def _log_object(obj: Any) -> str:
        log_string = f'{type(obj)} state:\n\n'

        for attribute, value in vars(obj).items():
            log_string += f'{attribute}: {value}\n'

        return log_string

    def log_crash(self, message: str) -> None:
        os.makedirs(self.log_dir, exist_ok=True)

        current_time = datetime.now().strftime('%Y_%m_%d-%H-%M-%S')
        log_path = os.path.join(self.log_dir, f'crash_{current_time}.txt')

        with open(log_path, 'w') as text_file:
            text_file.write(f'{message}\n')
            text_file.write(self._log_object(self.parent.canvas))
