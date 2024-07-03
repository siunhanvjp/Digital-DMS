from __future__ import annotations

from uuid import uuid4
from typing import Optional

from django.db import models
from document_management.models.document import Document, DocumentVersion
from user_account.models.user import User


# from metadata_management.models.metadata import MetadataValue

from math import ceil

from utils.exceptions.exceptions import NotFound
from utils.exceptions import NotFound, ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms.models import model_to_dict
from utils.enums.document import DocumentActionEnum
from django.utils import timezone
from django.core.paginator import Paginator


class EntryLogs(models.Model):
    uid = models.UUIDField(default=uuid4, editable=False, unique=True)
    modified_by = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="log_fk_user",
        db_constraint=False,
        db_column="user_id",
        blank=True,
        null=True,
    )
    document = models.ForeignKey(
        to=Document,
        on_delete=models.CASCADE,
        related_name="log_fk_document",
        db_constraint=False,
        db_column="document_id",
        blank=True,
        null=True,
    )
    document_version = models.ForeignKey(
        to=DocumentVersion,
        on_delete=models.CASCADE,
        related_name="log_fk_version",
        db_constraint=False,
        db_column="version_id",
        blank=True,
        null=True,
    )
    action = models.CharField(max_length=128, choices=DocumentActionEnum.choices)
    description = models.TextField(blank=True, editable=True)
    time = models.DateTimeField(default=timezone.now, editable=False)
