from enum import unique

from django.db.models import TextChoices


class UserDeviceTokenEnum(TextChoices):
    WEB_APP = "WEB_APP", "web app"
