from django.apps import AppConfig


class DocumentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "document"


class DocumentVersionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "document_version"
