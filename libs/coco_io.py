#!/usr/bin/env python
# -*- coding: utf8 -*-
import json
import os
from libs.constants import DEFAULT_ENCODING

COCO_EXT = '.json'
ENCODE_METHOD = DEFAULT_ENCODING
LABEL_MAP = [
    'die',
    'person'
]


class COCOWriter:

    def __init__(self, filename, img_size, shapes, output_file):
        self.filename = filename
        self.img_size = img_size
        self.shapes = shapes
        self.output_file = output_file

        self.box_list = []
        self.verified = False

    def write(self):
        if os.path.isfile(self.output_file):
            with open(self.output_file, "r") as json_file:
                output_data = json.load(json_file)
        else:
            output_data = {
                "images": [],
                "annotations": [],
                "categories": []
            }

            for category_id, label_name in enumerate(LABEL_MAP, start=1):
                output_data["categories"].append({
                    "id": category_id,
                    "name": label_name
                })

        image_ids = set()
        image_names = set()

        for image in output_data["images"]:
            image_ids.add(image["id"])
            image_names.add(image["file_name"])

        if self.filename in image_names:
            for image in output_data["images"]:
                if image["file_name"] == self.filename:
                    image_id = image["id"]
                    break
        else:
            image_id = self._get_new_id(image_ids)
            image_height, image_width, _ = self.img_size

            output_data["images"].append({
                "id": image_id,
                "width": image_width,
                "height": image_height,
                "file_name": self.filename
            })

        annotations = [anno for anno in output_data["annotations"]
                       if anno["image_id"] != image_id]
        output_data["annotations"] = annotations.copy()

        anno_ids = {anno["id"] for anno in output_data["annotations"]}

        for shape in self.shapes:
            points = shape["points"]

            x1 = points[0][0]
            y1 = points[0][1]
            x2 = points[1][0]
            y2 = points[2][1]

            x_min, y_min, width, height = self._calculate_coordinates(x1, x2, y1, y2)
            x_max, y_max = x_min + width, y_min + height

            anno_id = self._get_new_id(anno_ids)
            anno_ids.add(anno_id)

            label = shape["label"]
            category_id = LABEL_MAP.index(label) + 1

            annotation = {
                "id": anno_id,
                "image_id": image_id,
                "category_id": category_id,
                "area": width * height,
                "bbox": [int(x_min), int(y_min), int(width), int(height)],
                "iscrowd": 0,
                "segmentation": [
                    [x_max, y_min, x_max, y_max, x_min, y_max, x_min, y_min]
                ]
            }
            output_data["annotations"].append(annotation)

        with open(self.output_file, "w") as json_file:
            json.dump(output_data, json_file, indent=2)

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



class COCOReader:

    def __init__(self, json_path, file_path):
        self.json_path = json_path
        self.shapes = []
        self.verified = False
        self.filename = os.path.basename(file_path)
        try:
            self.parse_json()
        except ValueError as e:
            print("JSON decoding failed", e)

    def parse_json(self):
        with open(self.json_path, "r") as json_file:
            input_data = json.load(json_file)

        category_map = {cat["id"]: cat["name"] for cat in input_data['categories']}

        if len(self.shapes) > 0:
            self.shapes = []

        for image in input_data["images"]:
            if image["file_name"] == self.filename:
                image_id = image["id"]
                break
        else:
            return

        for anno in input_data["annotations"]:
            if anno["image_id"] == image_id:
                anno_name = category_map[anno["category_id"]]
                anno_bbox = anno["bbox"]

                if anno_bbox != [0, 0, 0, 0]:
                    self.add_shape(anno_name, anno_bbox)

    def add_shape(self, label, bnd_box):
        x_min, y_min, width, height = bnd_box
        x_max, y_max = x_min + width, y_min + height

        points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
        self.shapes.append((label, points, None, None, True))

    def get_shapes(self):
        return self.shapes
