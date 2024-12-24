class InvalidCOCOException(Exception):
    message = 'Could not parse the provided file. ' \
              'Are you sure it\'s a valid COCO dataset?'

    def __init__(self) -> None:
        Exception.__init__(self, self.message)
