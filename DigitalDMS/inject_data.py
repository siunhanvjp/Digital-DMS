import os
import sys
import json
from tqdm import tqdm
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DigitalDMS.settings")
django.setup()
from search_services.tasks import upload_to_els
from datetime import datetime
from django.conf import settings

from document_management.models.document import (
    Document as ModelDocument,
    DocumentVersion,
    DocumentPermission,
    MetadataValue,
    MetadataKey,
)
from entry_log_management.models.entry_log import EntryLogs
from user_account.models import User
from utils.enums.document import DocumentActionEnum, DocumentPermissionEnum
from django.forms.models import model_to_dict
from search_services.els_services.mappings import LegalDocument, vectorize_query, ContentChunk

USER_ID = 1
USER = User.objects.get(pk=USER_ID)

import random
from elasticsearch_dsl import (
    Index,
    Date,
    DenseVector,
    Document,
    InnerDoc,
    Keyword,
    Nested,
    Text,
    connections,
    MetaField,
    Boolean
)
import os

class ContentChunk(InnerDoc):
    chunk_content=Text()
    chunk_embedding=DenseVector(dims=768, index=True, similarity='cosine')

class LegalDocument(Document):
    # file specific field
    uid = Keyword()
    version_uid = Keyword()
    file_name  = Keyword()
    content  = Text()
    chunks = Nested(ContentChunk)
    is_lock = Boolean()
    is_private = Boolean()
    is_deleted = Boolean()
    
    class Meta:
        dynamic = MetaField("true")

    class Index:
        name = settings.SEARCH_INDEX
        
    def __init__(self, *args, **kwargs):
        if not LegalDocument._index.exists():
            LegalDocument._index.delete(ignore_unavailable=True)
            LegalDocument.init()
        if 'file_name' in kwargs:
            kwargs['file_name'] = os.path.splitext(kwargs['file_name'])[0]
        super().__init__(*args, **kwargs)

def generate_random_number():
    return random.randint(100, 200)

def generate_random_bool():
    return random.choice([True, False])

def upload_to_els(document_version_uid, law_data=None, skip_OCR=True):
    document_version = DocumentVersion.objects.select_related("document").get(uid=document_version_uid)
    # Default skip_OCR=True -> skip OCR -> using the same content or ""
    # TODO: get the file and perform OCR here
    print("starting")
    if not skip_OCR and law_data:
        content = law_data["content"]
        document_version.content = content
        document_version.save()
        
    metadata_values = document_version.value_fk_version.all()
    metadata_dict = {}
    # Initialize an empty dictionary to store key-value pairs
    if metadata_values.exists():
    
        # Iterate through metadata values and populate the dictionary
        for metadata_value in metadata_values:
            # Retrieve key and value for each metadata entry
            key = metadata_value.key.key  # Assuming 'key' field in MetadataKey is the actual key
            value = metadata_value.value
            # Add key-value pair to the dictionary
            metadata_dict[key] = value
    
    legal_doc = LegalDocument(
        uid=document_version.document.uid,
        version_uid=document_version_uid,
        file_name=document_version.file_name,
        content=document_version.content,
        is_lock = document_version.document.is_lock,
        is_private = document_version.document.is_private,
        is_deleted = document_version.document.is_deleted,
        **metadata_dict
    )
    if not skip_OCR and law_data:
        # if content is to changed
        for chunk_content, chunk_vector in zip(law_data["content_chunked"], law_data["content_vector"]):
            legal_doc.chunks.append(
                ContentChunk(chunk_content=chunk_content, chunk_embedding=chunk_vector)
            )
    legal_doc.save()
    
    return legal_doc.uid

def log_action(user, document, version, action, description):
        EntryLogs.objects.create(
            modified_by=user,
            document=document,
            document_version=version,
            action=action,
            description=description,
        )

def _create_metadata(metadata, document_version):
        created_metadata = []
        for item in metadata:
            for key, value in item.items():
                metadata_key, created = MetadataKey.objects.get_or_create(key=key)
                metadata_value = MetadataValue.objects.create(
                    value=value, key=metadata_key, document_version=document_version
                )
                created_metadata.append({key: value})
        return created_metadata

def create_document(
        file_index,
        user=USER,
        law_data=None,
        metadata=None,
        is_lock=False,
        is_private=True,
        is_deleted=False,
    ):
        folder_path = f"{user.username}/documents/"
        url = ""
        file_name = ""
        file_size = ""
        is_private = generate_random_bool()
        if law_data:
            file_size = generate_random_number()
            file_name = f"file_{file_index}.pdf"
            # Remove spaces from the file name and replace with underscores
            cleaned_file_name = file_name.replace(" ", "_")

            # Append _<datetime> to the file name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{cleaned_file_name}_{timestamp}"
        

        document = ModelDocument.objects.create(
            owner=user, is_lock=is_lock, is_private=is_private, is_deleted=is_deleted
        )
        document_version = DocumentVersion.objects.create(
            url=url,
            message="New Document",
            file_name=file_name,
            file_size=file_size,
            user=user,
            document=document,
        )
        DocumentPermission.objects.create(
            permission=DocumentPermissionEnum.EDIT, user=user, document=document
        )

        created_metadata = []
        if metadata:
            created_metadata = _create_metadata(metadata, document_version)
        ### UPLOAD TO ELS ###
        upload_to_els(document_version.uid, law_data, skip_OCR=False)
        #upload_to_els(document_version.uid, pickle.dumps(files.read()), skip_OCR=False)
        
        # Log the action
        log_action(
            user=user,
            document=document,
            version=document_version,
            action="CREATE",
            description=f"Document {file_name} created.",
        )

        return True
    
def delete_index(index_name):
    try:
        index = Index(index_name)
        if index.exists():
            index.delete()
            print(f"Index '{index_name}' deleted successfully.")
        else:
            print(f"Index '{index_name}' does not exist.")
    except Exception as e:
        print(f"Error deleting index '{index_name}': {e}")

if __name__ == "__main__":
    # DATASET_PATH = os.path.join(os.getcwd(), "law_vector_openai_full.json")
    DATASET_PATH = "/home/ubuntu/downloads/law_vector_openai_full.json"
    INDEX_NAME = settings.SEARCH_INDEX
    
    ModelDocument.objects.all().delete()
    delete_index(INDEX_NAME)
    
    map_eng_vie = {
        "title": "Tiêu đề",
        "summary": "Tóm tắt",
        "law_id": "Số",
        "tag": "Lĩnh vực"
    }

    with open(DATASET_PATH, 'r') as json_file:
        idx = 0
        dataset = json.load(json_file)
        for law_id, law_data in tqdm(dataset.items(), desc="Injecting Document"):
            idx += 1
            dumb_law_id = ["92/2000/qđ-nhnn", "73/2006/qh", '01/2011/tt-bca', "03/2003/qh11"]
            if law_id in dumb_law_id:
                law_data["title"] = ""
                law_data["summary"] = ""
                law_data["tag"] = ""
                
            formatted_data = [{"Số":law_id}]
            # Iterate through each column in the row
            for value in ['title', 'tag', 'summary']:
                formatted_data.append({map_eng_vie[value]: law_data[value]})
            create_document(idx, law_data=law_data, metadata=formatted_data)
            idx += 1