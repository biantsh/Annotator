#!/usr/bin/env python
# -*- coding: utf8 -*-
import json
import os
import tempfile
import threading
from collections import defaultdict
from libs.constants import DEFAULT_ENCODING

COCO_EXT = '.json'
ENCODE_METHOD = DEFAULT_ENCODING

class COCOIOHandler:

    def __init__(self, json_path, image_dir):
        self.json_path = json_path
        self.image_dir = image_dir

        self.shapes = []
        self.verified = False

        self.coco_dataset = None
        self.images = None
        self.annotations = None
        self.categories = {}

        self.image_ids = set()
        self.anno_ids = set()

        self.writer = ThreadedCocoWriter(json_path)

        if json_path is not None:
            try:
                self.parse_json()
            except ValueError as e:
                print("JSON decoding failed:", e)
            except FileNotFoundError:
                self.create_empty_json()

        else:
            self.create_empty_json()

    def parse_json(self):
        with open(self.json_path, "r") as json_file:
            self.coco_dataset = json.load(json_file)

        self.images = {image["file_name"]: image for image in self.coco_dataset["images"]}

        self.categories = {cat["id"]: cat["name"] for cat in self.coco_dataset["categories"]}

        self.annotations = defaultdict(lambda: [])
        for anno in self.coco_dataset["annotations"]:
            self.annotations[anno["image_id"]].append(anno)
            self.anno_ids.add(anno["id"])

    def create_empty_json(self):
        self.coco_dataset = {
            "images": [],
            "annotations": [],
            "categories": []
        }

        self.images = {}
        self.annotations = defaultdict(lambda: [])

    def load_shapes(self, file_path):
        file_name = os.path.basename(file_path)

        if file_name in self.images:
            coco_image = self.images[file_name]
        else:
            self.shapes = []
            return

        image_id = coco_image["id"]
        annotations = self.annotations[image_id]

        if len(self.shapes) > 0:
            self.shapes = []

        for anno in annotations:
            if anno["category_id"] not in self.categories:
                continue

            anno_name = self.categories[anno["category_id"]]
            anno_bbox = anno["bbox"]

            if anno_bbox != [0, 0, 0, 0]:
                self.add_shape(anno_name, anno_bbox)

    def add_image(self, image_name, image_size):
        image_width, image_height = image_size

        if image_name in self.images:
            return

        image_id = self._get_new_id(self.image_ids)
        self.image_ids.add(image_id)

        image = {
            "id": image_id,
            "width": image_width,
            "height": image_height,
            "file_name": image_name
        }

        self.coco_dataset["images"].append(image)
        self.images[image_name] = image

    def add_shape(self, label, bnd_box):
        x_min, y_min, width, height = bnd_box
        x_max, y_max = x_min + width, y_min + height

        points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
        self.shapes.append((label, points, None, None, True))

    def update_annotations(self, shapes, image_path, image_data, label_map):
        image_name = os.path.basename(image_path)
        self.shapes = shapes

        if image_name not in self.images:
            self.add_image(image_name, (image_data.width(), image_data.height()))

        image = self.images[image_name]
        image_id = image["id"]

        # Remove existing annotations for image
        remaining_annos = []
        for anno in self.coco_dataset["annotations"]:
            if anno["image_id"] == image_id:
                self.anno_ids.remove(anno["id"])
                self.annotations[anno["image_id"]] = []
            else:
                remaining_annos.append(anno)

        self.coco_dataset["annotations"] = remaining_annos.copy()

        for shape in shapes:
            points = shape["points"]

            x1 = points[0][0]
            y1 = points[0][1]
            x2 = points[1][0]
            y2 = points[2][1]

            x_min, y_min, width, height = self._calculate_coordinates(x1, x2, y1, y2)
            x_max, y_max = x_min + width, y_min + height

            anno_id = self._get_new_id(self.anno_ids)
            self.anno_ids.add(anno_id)

            label = shape["label"]
            try:
                category_id = label_map.index(label) + 1
            except ValueError:
                print('Warning: Tried to save annotation that is not present in label map.')
                continue

            annotation = {
                "id": anno_id,
                "image_id": image_id,
                "category_id": category_id,
                "area": int(width * height),
                "bbox": [int(x_min), int(y_min), int(width), int(height)],
                "iscrowd": 0,
                "segmentation": [
                    [int(x_max), int(y_min), int(x_max), int(y_max),
                     int(x_min), int(y_max), int(x_min), int(y_min)]
                ]
            }

            self.coco_dataset["annotations"].append(annotation)
            self.annotations[image_id].append(annotation)

        self.coco_dataset["categories"] = []
        for cat_id, name in enumerate(label_map, start=1):
            self.coco_dataset["categories"].append({
                'id': cat_id,
                'name': name
            })
            self.categories[cat_id] = name

        self.write()

    def write(self):
        self.writer.write(self.coco_dataset)

    def get_shapes(self):
        return self.shapes

    @staticmethod
    def _get_new_id(current_ids):
        new_id = 1

        while new_id in current_ids:
            new_id += 1

        return new_id

    @staticmethod
    def _calculate_coordinates(x1, x2, y1, y2):
        if x1 < x2:
            x_min = x1
            x_max = x2
        else:
            x_min = x2
            x_max = x1
        if y1 < y2:
            y_min = y1
            y_max = y2
        else:
            y_min = y2
            y_max = y1
        width = x_max - x_min
        if width < 0:
            width = width * -1
        height = y_max - y_min

        return x_min, y_min, width, height


class ThreadedCocoWriter:
    def __init__(self, file_path):
        self.file_path = file_path

        self.is_writing = False
        self.current_thread = None

    def _write(self, json_data):
        self.is_writing = True

        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                temp_filename = temp_file.name
                json.dump(json_data, temp_file, indent=2)
                temp_file.flush()

            os.replace(temp_filename, self.file_path)

        except Exception as e:
            print(f"Error while writing COCO annotation file: {e}")
        finally:
            self.is_writing = False

    def write(self, json_data):
        if self.is_writing:
            self.current_thread.join()  # Cancel current write before starting the new one

        self.current_thread = threading.Thread(target=self._write, args=(json_data,))
        self.current_thread.start()
