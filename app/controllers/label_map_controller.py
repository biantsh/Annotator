class LabelMapController:
    def __init__(self) -> None:
        self.label_map = []

    def load_labels(self, label_map_path: str) -> None:
        with open(label_map_path, 'r') as text_file:
            self.label_map = text_file.read().strip().split('\n')

    def get_label(self, label_id: int) -> str:
        return self.label_map[label_id]

    def get_id(self, label_name: str) -> int:
        return self.label_map.index(label_name)
