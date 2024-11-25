import json
from collections import defaultdict

from natsort import os_sorted

from app.objects import Bbox, Annotation


class AnnotationController:
    def __init__(self) -> None:
        self.labels = []
        self.images = {}

        self.bboxes = defaultdict(lambda: [])
        self.clipboard = []

    def get_annotations(self, image_name: str) -> list[Annotation]:
        return [Annotation.from_bbox(bbox) for bbox in self.bboxes[image_name]]

    def save_annotations(self, image_name: str, output_path: str) -> None:
        """Save annotations for a single image"""

    def import_annotations(self, annotations_path: str) -> None:
        with open(annotations_path, 'r') as json_file:
            coco_dataset = json.load(json_file)

        category_id_map = {}  # Mapping between imported and native IDs

        for category in coco_dataset['categories']:
            category_id = category['id']
            category_name = category['name']

            if category_name in self.labels:
                native_id = self.labels.index(category_name) + 1
                category_id_map[category_id] = native_id

        image_id_map = {}

        for image in coco_dataset['images']:
            image_name = image['file_name']
            image_id = image['id']
            width = image['width']
            height = image['height']

            image_id_map[image_id] = image_name
            self.images[image_name] = {
                'width': width,
                'height': height
            }

        for annotation in coco_dataset['annotations']:
            image_id = annotation['image_id']
            image_name = image_id_map[image_id]

            bbox = annotation['bbox']
            category_id = annotation['category_id']

            if category_id not in category_id_map:
                continue

            category_id = category_id_map[category_id]
            label_name = self.labels[category_id - 1]

            self.bboxes[image_name].append(
                Bbox.from_xywh(bbox, category_id, label_name))

    def export_annotations(self, output_path: str) -> None:
        coco_dataset = {
            'images': [],
            'annotations': [],
            'categories': []
        }

        image_names = os_sorted(self.images)
        annotation_id = 1

        for image_id, image_name in enumerate(image_names, start=1):
            image = self.images[image_name]

            coco_dataset['images'].append({
                'id': image_id,
                'width': image['width'],
                'height': image['height'],
                'file_name': image_name
            })

            for bbox in self.bboxes[image_name]:
                annotation = bbox.to_coco(annotation_id, image_id)
                coco_dataset['annotations'].append(annotation)

                annotation_id += 1

        for category_id, category in enumerate(self.labels, start=1):
            coco_dataset['categories'].append({
                'id': category_id,
                'name': category
            })

        with open(output_path, 'w') as json_file:
            json.dump(coco_dataset, json_file, indent=2)
