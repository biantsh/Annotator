import hashlib

import enchant

us_dict = enchant.Dict('en_US')


def clip_value(value: float, mininum: float, maximum: float) -> int | float:
    return min(max(value, mininum), maximum)


def text_to_color(text: str) -> tuple[int, int, int]:
    hash_code = int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16)

    red = hash_code % 255
    green = (hash_code // 255) % 255
    blue = (hash_code // 65025) % 255

    return red, green, blue


def pretty_text(text: str) -> str:
    words = text.replace('_', ' ').replace('-', ' ').split(' ')
    words = [word.capitalize() if us_dict.check(word) else word.upper()
             for word in words]

    return ' '.join(words)
