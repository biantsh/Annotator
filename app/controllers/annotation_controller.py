import json
import os
from collections import defaultdict
from typing import TYPE_CHECKING

from natsort import os_sorted

from app.objects import Bbox, Annotation

if TYPE_CHECKING:
    from annotator import MainWindow


class AnnotationController:
    def __init__(self, parent: 'MainWindow') -> None:
        self.parent = parent

        self.labels = []
        self.images = {}
        self.bboxes = defaultdict(lambda: [])

    def get_annotations(self, image_name: str) -> list[Annotation]:
        image_dir = self.parent.image_controller.image_dir
        annotator_dir = os.path.join(image_dir, '.annotator')

        json_name = f'{os.path.splitext(image_name)[0]}.json'
        json_path = os.path.join(annotator_dir, json_name)

        if not os.path.exists(json_path):
            return []

        with open(json_path, 'r') as json_file:
            json_content = json.load(json_file)

        return [Annotation(
            anno['position'], anno['category_id'], anno['label_name'])
            for anno in json_content['annotations']
        ]

    def save_annotations(self,
                         image_name: str,
                         image_size: tuple[int, int],
                         annotations: list[Annotation]
                         ) -> None:
        image_dir = self.parent.image_controller.image_dir
        annotator_dir = os.path.join(image_dir, '.annotator')

        os.makedirs(annotator_dir, exist_ok=True)

        json_name = f'{os.path.splitext(image_name)[0]}.json'
        json_path = os.path.join(annotator_dir, json_name)

        image_width, image_height = image_size
        annotation_info = [{
            'position': anno.position,
            'label_name': anno.label_name,
            'category_id': anno.category_id
        } for anno in annotations]

        with open(json_path, 'w') as json_file:
            json.dump({
                'image_width': image_width,
                'image_height': image_height,
                'annotations': annotation_info
            }, json_file, indent=2)

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
