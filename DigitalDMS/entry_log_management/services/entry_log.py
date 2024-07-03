from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage

from typing import Optional
from datetime import datetime
from math import ceil

import boto3
import requests

from ..models import (
    Document,
    DocumentVersion,
    DocumentPermission,
    MetadataValue,
    MetadataKey,
)
from user_account.models.user import User
from utils.enums.document import DocumentPermissionEnum
from utils.exceptions.exceptions import NotFound, ValidationError


class EntryLogService:
    def __init__(self):
        pass
