from ninja import ModelSchema
from ..models import Document


class DocumentResponse(ModelSchema):
    class Config:
        model = Document
        model_fields = ("is_lock", "is_private", "is_deleted")
