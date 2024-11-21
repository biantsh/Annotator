import glob
import os

from natsort import os_sorted
from PyQt5.QtGui import QImageReader


class ImageManager:
    def __init__(self):
        self.image_paths = []
        self.num_images = 0
        self.index = 0

    def load_images(self, dir_path):
        image_paths = []

        for extension in QImageReader.supportedImageFormats():
            extension = extension.data().decode()
            image_paths.extend(glob.glob(f'{dir_path}/*.{extension}'))

        self.image_paths = os_sorted(image_paths)
        self.num_images = len(self.image_paths)

    def get_image(self):
        return self.image_paths[self.index]

    def get_image_status(self):
        image_name = os.path.basename(self.get_image())
        return f'{image_name} [{self.index + 1}/{self.num_images}]'

    def next_image(self):
        self.index = (self.index + 1) % self.num_images

    def prev_image(self):
        self.index = (self.index - 1) % self.num_images
