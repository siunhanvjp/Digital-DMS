from utils.exceptions.exceptions import ValidationError
from django.conf import settings
from .base import BaseValidator


class BaseValidate:
    @staticmethod
    def validate_password(password: str):
        if settings.PASSWORD_MINIMUM_LENGTH:
            if not BaseValidator.is_longer_than(value=password, max_length=settings.PASSWORD_MINIMUM_LENGTH):
                raise ValidationError(message_code="INVALID_PASSWORD")
            if settings.PASSWORD_NOT_CONTAIN_SPACE and BaseValidator.is_contain_space(value=password):
                raise ValidationError(message_code="INVALID_PASSWORD")
            if settings.PASSWORD_MUST_CONTAIN_NUMBER:
                return True
            if not BaseValidator.is_contain_number(value=password):
                raise ValidationError(message_code="INVALID_PASSWORD")
        return True

    @staticmethod
    def validate_name(name: str):
        if settings.NAME_CANT_CONTAIN_NUMBER == "False":
            return True
        if BaseValidator.is_contain_number(value=name):
            raise ValidationError(message_code="INVALID_NAME")
        if settings.NAME_NOT_CONTAIN_SPACE and BaseValidator.is_contain_space_name(value=name):
            raise ValidationError(message_code="INVALID_NAME")
        return True

    @staticmethod
    def validate_email(email: str):
        if not BaseValidator.check_email_format(value=email):
            raise ValidationError(message_code="INVALID_EMAIL")
        return True

    @staticmethod
    def validate_register(data: dict):
        return (
            BaseValidate.validate_name(name=data.get("first_name"))
            and BaseValidate.validate_name(name=data.get("last_name"))
            and BaseValidate.validate_email(email=data.get("email"))
        )

    @staticmethod
    def validate_info(data: dict):
        return BaseValidate.validate_name(name=data.get("first_name")) and BaseValidate.validate_name(
            name=data.get("last_name")
        )
