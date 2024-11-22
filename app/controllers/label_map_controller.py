class LabelMapController:
    def __init__(self) -> None:
        self.labels = []

    def load_labels(self, label_map_path: str) -> None:
        with open(label_map_path, 'r') as text_file:
            self.labels = text_file.read().strip().split('\n')

    def get_label(self, label_id: int) -> str:
        return self.labels[label_id]

    def get_id(self, label_name: str) -> int:
        return self.labels.index(label_name)
