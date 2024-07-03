from enum import unique

from django.db.models import TextChoices


@unique
class DocumentPermissionEnum(TextChoices):
    VIEW = "VIEW", "view"
    EDIT = "EDIT", "edit"


class DocumentActionEnum(TextChoices):
    CREATE = "CREATE", "create"
    UPDATE = "UPDATE", "update"
    DELETE = "DELETE", "delete"
    PERMISSION_GRANTED = "PERMISSION_GRANTED", "permission_granted"
    PERMISSION_REMOVE = "PERMISSION_REMOVE", "permission_remove"
