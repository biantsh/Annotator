class LabelMapException(Exception):
    message = ''

    def __init__(self) -> None:
        Exception.__init__(self, self.message)


class InvalidJSONException(LabelMapException):
    message = 'Could not parse the provided label map. ' \
              'Are you sure it\'s a valid JSON file?'


class InvalidFormatException(LabelMapException):
    message = 'The provided label map does not match the expected format.'


class InvalidIDsException(LabelMapException):
    message = 'The IDs in the label map must be unique, positive integers.'


class InvalidNamesException(LabelMapException):
    message = 'The names in the label map must be unique strings.'


class LabelNotFoundException(LabelMapException):
    message = 'Could not find the specified label.'
