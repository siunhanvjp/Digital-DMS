import re

CONTAIN_NUMBER = "^(?=.*\d).+$"
EMAIL = "^[\w+\.-]+@[\w+\.-]+\.\w+$"
CONTAIN_SPACE = "^(?=.*\s).+$"
"""First name and last name must contain no numbers, 
no spaces allowed at the beginning or at the end, 
no two consecutive spaces in the middle."""
NAME_CONTAIN_SPACE = "^(?!.*\s$)(?!.*^\s)(?!.*\s{2,}).*$"


class BaseValidator(object):
    @staticmethod
    def is_longer_than(value: str, max_length: int) -> bool:
        return bool(len(value) >= max_length)

    @staticmethod
    def is_contain_number(value: str) -> bool:
        return bool(re.match(CONTAIN_NUMBER, value))

    @staticmethod
    def check_email_format(value: str):
        return bool(re.match(EMAIL, value))

    @staticmethod
    def is_contain_space(value: str):
        return bool(re.match(CONTAIN_SPACE, value))

    @staticmethod
    def is_contain_space_name(value: str):
        return not bool(re.match(NAME_CONTAIN_SPACE, value))
