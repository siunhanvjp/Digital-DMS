from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from .messages import CONTACT_ADMIN_FOR_SUPPORT, ERROR_MESSAGES


class BaseException(Exception):
    STATUS_CODE = 500
    DEFAULT_MESSAGE_CODE = CONTACT_ADMIN_FOR_SUPPORT

    def __init__(self, message_code: Optional[str] = None, error_code: Optional[str] = None, **kwargs):
        self.error_code = error_code or self.STATUS_CODE
        self.message_code = message_code or self.DEFAULT_MESSAGE_CODE
        self.message = kwargs.pop("message", ERROR_MESSAGES.get(self.message_code))
        self.field = kwargs.pop("field", None)
        self.format = kwargs.pop("format", None)
        self.format_field = kwargs.pop("context", None)

    def to_dict(self):
        if self.format_field:
            self.message = str(self.message).format(**self.format_field)

        return {"message_code": self.message_code, "message": self.message, "fields": self.field, "format": self.format}

    def __str__(self):
        if self.format_field:
            message = str(self.message).format(**self.format_field)
        else:
            message = self.message
        return f"[{self.message_code}] - {message}"


@dataclass(repr=False, eq=False)
class ExceptionQueue(Exception):
    __ERROR_MESSAGES = ERROR_MESSAGES

    # Load default exception message
    error_code: int = 500
    message_code: str = CONTACT_ADMIN_FOR_SUPPORT

    # For logging exceptions
    function_name: Optional[str] = None
    to_file: bool = False  # If true, log exception to file

    def __post_init__(self):
        self.__queue = []

    def log(self):
        # TODO: Log exception to file
        raise NotImplementedError()

    def add(self, exception: Exception):
        if isinstance(exception, (ExceptionQueue, BaseException)):
            self.error_code = int(exception.error_code)
        self.__queue.append(exception)

    def __add__(self, exception: Union[Exception, ExceptionQueue]):
        if isinstance(exception, (ExceptionQueue, BaseException)):
            self.error_code = int(exception.error_code)
        if isinstance(exception, ExceptionQueue):
            self.__queue.extend(exception.__queue)
        else:
            self.add(exception)
        return self

    def __bool__(self):
        return bool(self.__queue)

    def __str__(self):
        return "\n".join([str(exception) for exception in self.__queue])

    def clear(self):
        self.__queue.clear()

    def to_response(self):
        queue, errors = self.__queue.copy(), []

        message_code = self.message_code
        message = self.__ERROR_MESSAGES.get(self.message_code)

        for ordinal, exception in enumerate(queue):
            if ordinal == 0:
                if isinstance(exception, BaseException):
                    exception.to_dict()
                    message_code = exception.message_code
                    message = exception.message
                else:
                    message_code = self.message_code

            if isinstance(exception, BaseException):
                errors.append(exception.to_dict())
            else:
                message_code = getattr(exception, "message_code", self.message_code)

                errors.append(
                    {
                        "message_code": message_code,
                        "ordinal": ordinal,
                        "fields": getattr(exception, "fields", None),
                        "format": getattr(exception, "format", None),
                    }
                )

        self.__queue = []

        return {
            "data": None,
            "errors": errors,
            "error_code": self.error_code,
            "message_code": message_code,
            "message": message,
        }
