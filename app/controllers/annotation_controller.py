import json
import os
import shutil
from collections import defaultdict
from typing import TYPE_CHECKING

from natsort import os_sorted

from app.objects import Annotation

if TYPE_CHECKING:
    from annotator import MainWindow


class AnnotationController:
    def __init__(self, parent: 'MainWindow') -> None:
        self.parent = parent
        self.labels = []

    def load_annotations(self, image_name: str) -> dict:
        image_dir = self.parent.image_controller.image_dir
        annotator_dir = os.path.join(image_dir, '.annotator')

        json_name = f'{os.path.splitext(image_name)[0]}.json'
        json_path = os.path.join(annotator_dir, json_name)

        if not os.path.exists(json_path):
            return {'image': None, 'annotations': []}

        with open(json_path, 'r') as json_file:
            json_content = json.load(json_file)

        return {
            'image': json_content['image'],
            'annotations': [Annotation(
                anno['position'], anno['category_id'], anno['label_name'])
                for anno in json_content['annotations']]
        }

    def save_annotations(self,
                         image_name: str,
                         image_size: tuple[int, int],
                         annotations: list[Annotation],
                         append: bool = False
                         ) -> None:
        image_dir = self.parent.image_controller.image_dir
        annotator_dir = os.path.join(image_dir, '.annotator')

        os.makedirs(annotator_dir, exist_ok=True)

        json_name = f'{os.path.splitext(image_name)[0]}.json'
        json_path = os.path.join(annotator_dir, json_name)

        image_width, image_height = image_size
        annotation_content = {
            'image': {
                'width': image_width,
                'height': image_height
            },
            'annotations': []
        }

        if append and os.path.exists(json_path):
            with open(json_path, 'r') as json_file:
                annotation_content['annotations'] = \
                    json.load(json_file)['annotations']

        for anno in annotations:
            anno_info = {
                'position': anno.position,
                'label_name': anno.label_name,
                'category_id': anno.category_id
            }

            if anno_info not in annotation_content['annotations']:
                annotation_content['annotations'].append(anno_info)

        with open(json_path, 'w') as json_file:
            json.dump(annotation_content, json_file, indent=2)

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

        annotation_map = defaultdict(lambda: [])

        for annotation in coco_dataset['annotations']:
            image_id = annotation['image_id']

            bbox = annotation['bbox']
            category_id = annotation['category_id']

            if category_id not in category_id_map:
                continue

            category_id = category_id_map[category_id]
            label_name = self.labels[category_id - 1]

            annotation = Annotation.from_xywh(bbox, category_id, label_name)
            annotation_map[image_id].append(annotation)

        for image in coco_dataset['images']:
            image_name = image['file_name']
            image_id = image['id']
            width = image['width']
            height = image['height']

            annotations = annotation_map[image_id]
            self.save_annotations(image_name,
                                  (width, height),
                                  annotations,
                                  append=True)

    def export_annotations(self, output_path: str) -> None:
        image_paths = self.parent.image_controller.image_paths
        image_dir = self.parent.image_controller.image_dir

        annotator_dir = os.path.join(image_dir, '.annotator')
        if not os.path.exists(annotator_dir):
            return

        export_content = {
            'images': [],
            'annotations': [],
            'categories': []
        }

        annotation_id = 1

        for image_id, image_path in enumerate(os_sorted(image_paths), 1):
            image_name = os.path.basename(image_path)

            anno_info = self.load_annotations(image_name)
            image, annotations = anno_info['image'], anno_info['annotations']

            if image is None:
                continue

            export_content['images'].append({
                'id': image_id,
                'width': image['width'],
                'height': image['height'],
                'file_name': image_name
            })

            for annotation in annotations:
                annotation_coco = annotation.to_coco(annotation_id, image_id)
                export_content['annotations'].append(annotation_coco)

                annotation_id += 1

        for category_id, category_name in enumerate(self.labels, 1):
            export_content['categories'].append({
                'id': category_id,
                'name': category_name
            })

        with open(output_path, 'w') as json_file:
            json.dump(export_content, json_file, indent=2)

        shutil.rmtree(annotator_dir)
        self.parent.reload()

    def has_annotations(self) -> bool:
        image_paths = self.parent.image_controller.image_paths

        if not image_paths:
            return False

        for image_path in image_paths:
            image_name = os.path.basename(image_path)
            annotations = self.load_annotations(image_name)

            if annotations['annotations']:
                return True

        return False
