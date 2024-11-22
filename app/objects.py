class Bbox:
    def __init__(self, position: tuple[int, ...], category_id: int) -> None:
        self.position = position
        self.category_id = category_id

    @classmethod
    def from_xywh(cls, position: tuple[int, ...], category_id: int) -> 'Bbox':
        x_min, y_min, width, height = position
        x_max, y_max = x_min + width, y_min + height

        return cls((x_min, y_min, x_max, y_max), category_id)

    @property
    def left(self) -> int:
        return self.position[0]

    @property
    def top(self) -> int:
        return self.position[1]

    @property
    def right(self) -> int:
        return self.position[2]

    @property
    def bottom(self) -> int:
        return self.position[3]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def xyxy(self) -> tuple[int, ...]:
        return self.position

    @property
    def xywh(self) -> tuple[int, ...]:
        return self.left, self.top, self.width, self.height

    def to_coco(self, object_id: int, image_id: int) -> dict:
        return {
            'id': object_id,
            'image_id': image_id,
            'category_id': self.category_id,
            'area': self.area,
            'bbox': self.xywh,
            'iscrowd': 0,
            'segmentation': [
                [self.right, self.top, self.right, self.bottom,
                 self.left, self.bottom, self.left, self.top]
            ]
        }
