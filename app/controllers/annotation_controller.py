import hashlib
import json
import os
import shutil
from collections import defaultdict
from typing import TYPE_CHECKING

from natsort import os_sorted

from app.exceptions.coco import InvalidCOCOException
from app.objects import Annotation

if TYPE_CHECKING:
    from annotator import MainWindow


class AnnotationController:
    def __init__(self, parent: 'MainWindow') -> None:
        self.parent = parent

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
            'annotations': [Annotation(anno['position'], anno['label_name'])
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
                'label_name': anno.label_name
            }

            if anno_info not in annotation_content['annotations']:
                annotation_content['annotations'].append(anno_info)

        with open(json_path, 'w') as json_file:
            json.dump(annotation_content, json_file, indent=2)

    def _import_annotations(self, coco_dataset: dict) -> None:
        annotations = defaultdict(lambda: [])

        label_names = {category['id']: category['name']
                       for category in coco_dataset['categories']}

        for annotation in coco_dataset['annotations']:
            category_id = annotation['category_id']
            image_id = annotation['image_id']

            bbox = annotation['bbox']
            label_name = label_names[category_id]

            annotation = Annotation.from_xywh(bbox, label_name)
            annotations[image_id].append(annotation)

        for image in coco_dataset['images']:
            image_name = image['file_name']
            image_id = image['id']
            width = image['width']
            height = image['height']

            self.save_annotations(image_name,
                                  (width, height),
                                  annotations[image_id],
                                  append=True)

    def import_annotations(self, annotations_path: str) -> bool:
        image_dir = self.parent.image_controller.image_dir
        annotator_dir = os.path.join(image_dir, '.annotator')
        imports_path = os.path.join(annotator_dir, '.imports.json')

        with open(annotations_path, 'r') as json_file:
            try:
                coco_dataset = json.load(json_file)
                annotations = coco_dataset['annotations']
            except (json.JSONDecodeError, TypeError):
                raise InvalidCOCOException()

        anno_data = json.dumps(annotations, sort_keys=True)
        hashed_data = hashlib.sha256(anno_data.encode('utf-8')).hexdigest()

        # Check if the same file path or contents have already been imported
        existing_imports = {'file_paths': [], 'hashes': []}
        if os.path.exists(imports_path):
            with open(imports_path, 'r') as json_file:
                existing_imports = json.load(json_file)

        if (annotations_path in existing_imports['file_paths']
                or hashed_data in existing_imports['hashes']):
            return False

        try:
            self._import_annotations(coco_dataset)
        except KeyError:
            raise InvalidCOCOException()

        # Update and save the existing imports
        existing_imports['file_paths'].append(annotations_path)
        existing_imports['hashes'].append(hashed_data)

        os.makedirs(annotator_dir, exist_ok=True)
        with open(imports_path, 'w') as json_file:
            json.dump(existing_imports, json_file, indent=2)

        return True

    def export_annotations(self, output_path: str) -> bool:
        image_paths = self.parent.image_controller.image_paths
        image_dir = self.parent.image_controller.image_dir

        annotator_dir = os.path.join(image_dir, '.annotator')
        if not os.path.exists(annotator_dir):
            return False

        label_map = self.parent.label_map_controller
        categories = sorted(label_map.labels, key=lambda item: item['id'])

        export_content = {
            'images': [],
            'annotations': [],
            'categories': categories
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

            for anno in annotations:
                category_id = label_map.get_id(anno.label_name)

                export_content['annotations'].append({
                    'id': annotation_id,
                    'image_id': image_id,
                    'category_id': category_id,
                    'area': anno.area,
                    'bbox': anno.xywh,
                    'iscrowd': 0,
                    'segmentation': [
                        [anno.right, anno.top, anno.right, anno.bottom,
                         anno.left, anno.bottom, anno.left, anno.top]
                    ]
                })
                annotation_id += 1

        with open(output_path, 'w') as json_file:
            json.dump(export_content, json_file, indent=2)

        shutil.rmtree(annotator_dir)
        return True

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
