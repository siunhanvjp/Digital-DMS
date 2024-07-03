from .base import BaseException


class ValidationError(BaseException):
    STATUS_CODE = 400
    DEFAULT_MESSAGE_CODE = "VALIDATION_ERROR"


class ParseError(BaseException):
    STATUS_CODE = 400
    DEFAULT_MESSAGE_CODE = "PARSE_ERROR"


class AuthenticationFailed(BaseException):
    STATUS_CODE = 401
    DEFAULT_MESSAGE_CODE = "AUTHENTICATION_FAILED"


class NotAuthenticated(BaseException):
    STATUS_CODE = 401
    DEFAULT_MESSAGE_CODE = "NOT_AUTHENTICATED"


class NotFound(BaseException):
    STATUS_CODE = 404
    DEFAULT_MESSAGE_CODE = "NOT_FOUND"


class PermissionDenied(BaseException):
    STATUS_CODE = 403
    DEFAULT_MESSAGE_CODE = "PERMISSION_DENIED"
