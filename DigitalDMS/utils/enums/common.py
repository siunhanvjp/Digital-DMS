from enum import unique

from django.db.models import TextChoices


@unique
class SortTypeEnum(TextChoices):
    ASC = "asc"
    DESC = "desc"
