from typing import Optional

from ninja.schema import Schema
from utils.enums.document import DocumentPermissionEnum


class DocumentRequest(Schema):
    metadata: list
    message: str


class DocumentPermissionGrant(Schema):
    email: str
    document_uid: str
    permission: DocumentPermissionEnum


class DocumentPermissionUnGrant(Schema):
    email: str
    document_uid: str
    
class KeyRequest(Schema):
    key: str
    threshold: float = 0.8
