from elasticsearch_dsl import Search
from celery import shared_task
from search_services.els_services.mappings import LegalDocument, vectorize_query, ContentChunk, MetadataKeyDoc
from document_management.models import DocumentVersion, MetadataKey
from search_services.services import ocr_docs, chunking_content
import pickle
from django.conf import settings

@shared_task(max_retries=0)
def upload_to_els(document_version_uid, document_file=None, skip_OCR=True):
    document_version = DocumentVersion.objects.select_related("document").get(uid=document_version_uid)
    # Default skip_OCR=True -> skip OCR -> using the same content or ""
    # TODO: get the file and perform OCR here
    if not skip_OCR and document_file:
        content = ocr_docs(pickle.loads(document_file))
        document_version.content = content
        document_version.save()
        #print(content)
        
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
    if not skip_OCR and document_file:
        # if content is to changed
        chunks = chunking_content(content)
        for chunk_content, chunk_vector in chunks:
            legal_doc.chunks.append(
                ContentChunk(chunk_content=chunk_content, chunk_embedding=chunk_vector)
            )
    
    search_results = LegalDocument.search().filter('term', uid=legal_doc.uid)
    existing_doc = None
    
    try:
        # Try to retrieve the document from the search results
        existing_doc = search_results.execute().hits[0]
    except IndexError:
        pass  # No existing document found

    if existing_doc:
        # Update the existing document
        doc = LegalDocument.get(id=existing_doc.meta.id)
        doc.version_uid = legal_doc.version_uid,
        doc.content = legal_doc.content
        doc.file_name = legal_doc.file_name
        doc.chunks = legal_doc.chunks
        doc.is_lock = legal_doc.is_lock,
        doc.is_private = legal_doc.is_private,
        doc.is_deleted = legal_doc.is_deleted,
        # Include additional fields from metadata_dict
        for key, value in metadata_dict.items():
            setattr(doc, key, value)
            
        doc.save()
    else:
        # Save the new document
        legal_doc.save()
        
    return legal_doc.uid

@shared_task(max_retries=0)
def sync_metadata(missing_keys):
    print(missing_keys)
    for key in missing_keys:
        key_doc = MetadataKeyDoc(key=key)
        key_doc.save()
    return True
    
@shared_task(max_retries=0)
def delete_document_els(uid_value, is_soft=False):
        
    s = Search(index=settings.SEARCH_INDEX).query("match", uid=uid_value)
    try:
        existing_doc = s.execute().hits[0]
    except IndexError:
        existing_doc = None

    if existing_doc:
        if is_soft:
            # Retrieve the document using the Document subclass
            doc = LegalDocument.get(id=existing_doc.meta.id)
            doc.is_deleted = True
            doc.save()
        else:
            # Hard delete
            LegalDocument.get(id=existing_doc.meta.id).delete()