class IOException(Exception):
    message = ''

    def __init__(self) -> None:
        Exception.__init__(self, self.message)


class InvalidCOCOException(IOException):
    message = 'Could not parse the provided file. ' \
              'Are you sure it\'s a valid COCO dataset?'


class InvalidLabelException(IOException):
    message = 'Some of the annotations to export ' \
              'are missing from the label map.'


class InvalidSchemaException(IOException):
    message = 'Some of the annotations to export have keypoint ' \
              'definitions that don\'t match the current label map'
