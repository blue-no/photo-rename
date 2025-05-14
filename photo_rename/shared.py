from enum import Enum, auto


class NamingMethod(Enum):
    DATE_ONLY = 0
    DATE_BEFORE_ORIGINAL = 1
    DATE_AFTER_ORIGINAL = 2


class RenameResult(Enum):
    SUCCESS = auto()
    FAILURE = auto()
