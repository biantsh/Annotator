import glob
import os

from natsort import os_sorted
from PyQt6.QtGui import QImageReader

from app.utils import clip_value


class ImageController:
    def __init__(self) -> None:
        self.image_dir = None

        self.image_paths = []
        self.num_images = 0
        self.index = 0

    def load_images(self, image_dir: str) -> None:
        self.image_dir = image_dir

        image_paths = []
        self.index = 0

        for extension in QImageReader.supportedImageFormats():
            extension = extension.data().decode()
            image_paths.extend(glob.glob(f'{image_dir}/*.{extension}'))

        self.image_paths = os_sorted(image_paths)
        self.num_images = len(self.image_paths)

    def get_image_path(self) -> str:
        return self.image_paths[self.index]

    def get_image_name(self) -> str:
        return os.path.basename(self.get_image_path())

    def get_image_status(self) -> str:
        return f'{self.get_image_name()} [{self.index + 1}/{self.num_images}]'

    def next_image(self) -> None:
        self.index = clip_value(self.index + 1, 0, self.num_images - 1)

    def prev_image(self) -> None:
        self.index = clip_value(self.index - 1, 0, self.num_images - 1)

    def go_to_image(self, index: int) -> None:
        self.index = clip_value(index - 1, 0, self.num_images - 1)
