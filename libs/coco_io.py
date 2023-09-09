#!/usr/bin/env python
# -*- coding: utf8 -*-
import json
import os
from libs.constants import DEFAULT_ENCODING

COCO_EXT = '.json'
ENCODE_METHOD = DEFAULT_ENCODING


class COCOWriter:

    def __init__(self, folder_name, filename, img_size, database_src='Unknown', local_img_path=None):
        self.folder_name = folder_name
        self.filename = filename
        self.database_src = database_src
        self.img_size = img_size
        self.box_list = []
        self.local_img_path = local_img_path
        self.verified = False


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
