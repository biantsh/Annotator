import hashlib
import json
import os
import shutil
from collections import defaultdict
from typing import TYPE_CHECKING

from natsort import os_sorted

from app.controllers.label_map_controller import (
    LabelMapController,
    LabelSchema
)
from app.exceptions.io import (
    InvalidCOCOException,
    InvalidLabelException,
    InvalidSchemaException
)
from app.objects import Annotation, Keypoint

if TYPE_CHECKING:
    from annotator import MainWindow


class AnnotationController:
    def __init__(self, parent: 'MainWindow') -> None:
        self.parent = parent

    @property
    def label_map(self) -> LabelMapController:
        return self.parent.label_map_controller

    def load_annotations(self, image_name: str) -> dict:
        image_dir = self.parent.image_controller.image_dir
        annotator_dir = os.path.join(image_dir, '.annotator')

        json_name = f'{os.path.splitext(image_name)[0]}.json'
        json_path = os.path.join(annotator_dir, json_name)

        if not os.path.exists(json_path):
            return {'image': None, 'annotations': []}

        with open(json_path, 'r') as json_file:
            json_content = json.load(json_file)

        annotations = {
            'image': json_content['image'],
            'annotations': []
        }

        for anno in json_content['annotations']:
            label_schema = LabelSchema(**anno['label_schema'])
            label_name = label_schema.label_name

            if self.label_map.contains(label_name):
                loaded_schema = self.label_map.get_label_schema(label_name)

                if loaded_schema.kpt_names == label_schema.kpt_names:
                    label_schema.kpt_symmetry = loaded_schema.kpt_symmetry

            position = anno['position']
            annotation = Annotation(position, label_schema, ref_id=anno['id'])

            annotation.keypoints = [
                Keypoint(annotation, [pos_x, pos_y], visible)
                for pos_x, pos_y, visible in anno['keypoints']]

            annotations['annotations'].append(annotation)

        return annotations

    def save_annotations(self,
                         image_name: str,
                         image_size: tuple[int, int],
                         annotations: list[Annotation],
                         append: bool = False
                         ) -> None:
        image_dir = self.parent.image_controller.image_dir
        annotator_dir = os.path.join(image_dir, '.annotator')

        json_name = f'{os.path.splitext(image_name)[0]}.json'
        json_path = os.path.join(annotator_dir, json_name)

        anno_data = []
        if append and os.path.exists(json_path):
            with open(json_path, 'r') as json_file:
                anno_data = json.load(json_file)['annotations']

        pos_data = [anno['position'] for anno in anno_data]
        image_data = {
            'image': {
                'width': image_size[0],
                'height': image_size[1]
            },
            'annotations': anno_data
        }

        for anno in annotations:
            if anno.position in pos_data:
                continue

            label_schema = anno.label_schema.to_dict()
            keypoints = [[keypoint.pos_x,
                          keypoint.pos_y,
                          keypoint.visible]
                         for keypoint in anno.keypoints]

            image_data['annotations'].append({
                'position': anno.position,
                'label_schema': label_schema,
                'keypoints': keypoints,
                'id': anno.ref_id
            })

        os.makedirs(annotator_dir, exist_ok=True)
        with open(json_path, 'w') as json_file:
            json.dump(image_data, json_file, indent=2)

    def _import_annotations(self, coco_dataset: dict) -> None:
        annotations = defaultdict(lambda: [])

        category_index = {category['id']: category
                          for category in coco_dataset['categories']}

        for coco_annotation in coco_dataset['annotations']:
            category_id = coco_annotation['category_id']
            image_id = coco_annotation['image_id']
            bbox = coco_annotation['bbox']

            category = category_index[category_id]
            category_name = category['name']

            has_keypoints = 'keypoints' in coco_annotation \
                and coco_annotation['keypoints']

            if self.label_map.contains(category_name) and not has_keypoints:
                label_schema = self.label_map.get_label_schema(category_name)

            else:
                label_schema = LabelSchema(
                    category_name,
                    category.get('keypoints', []),
                    category.get('skeleton', []),
                    category.get('symmetry', [])
                )

            annotation = Annotation.from_xywh(bbox, label_schema)
            annotations[image_id].append(annotation)

            keypoints = coco_annotation.get('keypoints', [])
            if len(keypoints) != 3 * len(label_schema.kpt_names):
                continue

            annotation.keypoints = [
                Keypoint(annotation, [pos_x, pos_y], bool(visibility))
                for pos_x, pos_y, visibility in zip(*[iter(keypoints)] * 3)]

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
                if not label_map.contains(anno.label_name):
                    raise InvalidLabelException()

                category_id = label_map.get_id(anno.label_name)
                label_schema = label_map.get_label_schema(anno.label_name)

                annotation = {
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
                }

                if anno.has_keypoints:
                    if anno.kpt_names != label_schema.kpt_names:
                        raise InvalidSchemaException()

                    keypoints, num_keypoints = [], 0

                    for keypoint in anno.keypoints:
                        if keypoint.visible:
                            keypoints.extend([*keypoint.position, 2])
                            num_keypoints += 1
                        else:
                            keypoints.extend([0, 0, 0])

                    annotation['keypoints'] = keypoints
                    annotation['num_keypoints'] = num_keypoints

                export_content['annotations'].append(annotation)
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
