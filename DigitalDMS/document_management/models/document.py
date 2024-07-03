from __future__ import annotations

from uuid import uuid4
from typing import Optional

from django.db import models
from user_account.models.user import User

# from metadata_management.models.metadata import MetadataValue

from math import ceil

from utils.exceptions.exceptions import NotFound
from utils.exceptions import NotFound, ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms.models import model_to_dict
from utils.enums.document import DocumentPermissionEnum
from django.utils import timezone
from django.core.paginator import Paginator



class Document(models.Model):
    uid = models.UUIDField(default=uuid4, editable=False, unique=True)
    owner = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="document_fk_user",
        db_constraint=False,
        db_column="user_id",
        blank=True,
        null=True,
    )
    is_lock = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    create_date = models.DateTimeField(default=timezone.now, editable=False)
    updated_date = models.DateTimeField(auto_now=True)

    @staticmethod
    def get_by_uid(uid: str):
        try:
            return Document.objects.get(uid=uid)
        except Document.DoesNotExist as e:
            raise NotFound(message_code="DOCUMENT_NOT_FOUND") from e
        except Document.MultipleObjectsReturned as e:
            raise ValidationError(message_code="MORE_THAN_ONE_DOCUMENT_FOUND") from e
        except DjangoValidationError:
            raise ValidationError(message_code="INVALID_UID")


class DocumentVersion(models.Model):
    uid = models.UUIDField(default=uuid4, editable=False, unique=True)
    url = models.TextField(blank=True, editable=True)
    message = models.TextField(blank=True, editable=True)
    file_name = models.TextField(blank=True)
    file_size = models.TextField(max_length=255, blank=True)
    content = models.TextField(blank=True, editable=True)
    next_version = models.ForeignKey(
        to="DocumentVersion",
        on_delete=models.CASCADE,
        related_name="version_fk_version",
        db_constraint=False,
        db_column="next_version_id",
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="version_fk_user",
        db_constraint=False,
        db_column="user_id",
        blank=True,
        null=True,
    )
    document = models.ForeignKey(
        to=Document,
        on_delete=models.CASCADE,
        related_name="version_fk_document",
        db_constraint=False,
        db_column="document_id",
        blank=True,
        null=True,
    )
    create_date = models.DateTimeField(default=timezone.now, editable=False)
    updated_date = models.DateTimeField(auto_now=True)

    @staticmethod
    def get_latest_version(document: Document):
        try:
            return DocumentVersion.objects.get(document=document, next_version=None)
        except DocumentVersion.DoesNotExist as e:
            raise NotFound(message_code="DOCUMENT_VERSION_NOT_FOUND") from e
        except DocumentVersion.MultipleObjectsReturned as e:
            raise ValidationError(
                message_code="MORE_THAN_ONE_DOCUMENT_VERSION_FOUND"
            ) from e
        except DjangoValidationError:
            raise ValidationError(message_code="INVALID_UID")


class DocumentPermission(models.Model):
    uid = models.UUIDField(default=uuid4, editable=False, unique=True)
    permission = models.CharField(max_length=10, choices=DocumentPermissionEnum.choices)
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="permission_fk_user",
        db_constraint=False,
        db_column="user_id",
        blank=True,
        null=True,
    )
    document = models.ForeignKey(
        to=Document,
        on_delete=models.CASCADE,
        related_name="permission_fk_document",
        db_constraint=False,
        db_column="document_id",
        blank=True,
        null=True,
    )

    @staticmethod
    def has_permission(user, document, permission):
        return DocumentPermission.objects.filter(
            user=user, document=document, permission=permission
        ).exists()


class MetadataKey(models.Model):
    uid = models.UUIDField(default=uuid4, editable=False, unique=True)
    key = models.CharField(max_length=255, blank=True, null=True)


class MetadataValue(models.Model):
    uid = models.UUIDField(default=uuid4, editable=False, unique=True)
    value = models.TextField(blank=True, null=True)
    key = models.ForeignKey(
        to=MetadataKey,
        on_delete=models.CASCADE,
        related_name="value_fk_key",
        db_constraint=False,
        db_column="key_id",
        blank=True,
        null=True,
    )
    document_version = models.ForeignKey(
        to=DocumentVersion,
        on_delete=models.CASCADE,
        related_name="value_fk_version",
        db_constraint=False,
        db_column="version_id",
        blank=True,
        null=True,
    )