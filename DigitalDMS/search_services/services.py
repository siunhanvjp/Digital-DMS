import io
import ocrmypdf
import pdfplumber
from openai import OpenAI
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from datetime import datetime
from django.conf import settings
from document_management.models import Document, DocumentPermission, DocumentVersion, MetadataValue, MetadataKey
from django.forms.models import model_to_dict
from entry_log_management.models.entry_log import EntryLogs
from utils.enums.document import DocumentActionEnum, DocumentPermissionEnum
from django.http import JsonResponse
from search_services.els_services.mappings import LegalDocument, ContentChunk

def check_text_in_pdf(pdf_file):
    with pdfplumber.open(io.BytesIO(pdf_file)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                return True
    return False

def ocr_docs(pdf_file, pages=None):
    # Receive a pdf file and generate the content
    ocrmypdf.configure_logging(verbosity=ocrmypdf.Verbosity.quiet)
    pdf_content = pdf_file  # Read the PDF content into memory

    if not check_text_in_pdf(pdf_file):
        with io.BytesIO() as output_buffer:
            # Perform OCR on the PDF content
            
            ocrmypdf.ocr(io.BytesIO(pdf_content), output_buffer, output_type='pdf',deskew=True,
                        language=['vie'], invalidate_digital_signatures= True, optimize=0, pages=pages)
            # Reset the buffer position
            output_buffer.seek(0)
            # Read the OCR'd PDF content into memory
            ocr_pdf_content = output_buffer.read()
    else:
        ocr_pdf_content = pdf_file

    #pdf_document = fitz.open(stream=pdf_file.read())
    # doc = fitz.open("pdf", ocr_pdf_content)
    
    with io.BytesIO(ocr_pdf_content) as ocr_pdf_io:
        with pdfplumber.open(ocr_pdf_io) as pdf:
            # Extract text from the first page
            if pages == "1":
                raw_text = ""
                if pdf.pages:
                    raw_text = pdf.pages[0].extract_text()
            else:
                # Extract text from the whole document
                raw_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        raw_text += text + "\n"
    return raw_text

def generate_metadata(content):
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": "Extract the possible document metadata from the legal document text provided (this is the first page of the document), return the result in Vietnamese with the JSON format \"metadata\":\"value\", correct any grammatical errors, this is the set of metadata with its type hinting in python, it must strictly follow this:\n\"Loại văn bản\": (type: str)\n\"Số\": (type: str)\n\"Ngày ban hành\": (type: str)\n\"Đơn vị ban hành\": (type: str)\n\"Căn cứ\": (type: List[str], top 3 relevant item)\n\"Tiêu đề\": (type: str)\n\"Lĩnh vực\": (type: str)"
                }
            ]
            },
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": content
                }
            ]
            },
            {
            "role": "assistant",
            "content": [
                {
                "type": "text",
                "text": "{\n    \"Loại văn bản\": \"\",\n    \"Số\": \"\",\n    \"Ngày ban hành\": \"\",\n    \"Đơn vị ban hành\": \"\",\n    \"Căn cứ\": [],\n    \"Tiêu đề\": \"\",\n    \"Lĩnh vực\": \"\"\n}"
                }
            ]
            }
        ],
        temperature=0.1,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    # print(response.choices[0].message.content)
    metadata = json.loads(response.choices[0].message.content)
    #print(response.choices[0].message.content)
    return (metadata)

def get_openai_embedding_batch(batch, model="text-embedding-3-large"):
    client = OpenAI()
    batch = [text.replace("\n", " ") for text in batch]
    data = client.embeddings.create(input = batch,
                                   model=model,
                                   dimensions=768).data
    return [item.embedding for item in data]

def chunking_content(content):
    CHUNK_SIZE = 600
    CHUNK_OVERLAP = 100
    MAX_BATCH_SIZE = 12
    
    content_chunked = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-4",
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    ).split_text(content) 
    
    content_vectors = []
    batch_content_chunks = []
    for content_chunk in content_chunked:
        batch_content_chunks.append(content_chunk)
        if len(batch_content_chunks) >= MAX_BATCH_SIZE:
            batch_content_vectors = get_openai_embedding_batch(batch_content_chunks)
            content_vectors.extend(batch_content_vectors)
            batch_content_chunks = []
    if batch_content_chunks:
        # Process the remaining batch
        batch_content_vectors = get_openai_embedding_batch(batch_content_chunks)
        content_vectors.extend(batch_content_vectors)
    return zip(content_chunked, content_vectors)

def convert_to_custom_format(metadata): 
    return [{key:value} for key,value in metadata.items()]

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


def inject_to_els(document_version_uid, content):
    document_version = DocumentVersion.objects.select_related("document").get(uid=document_version_uid)

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
        existing_doc.version_uid = legal_doc.version_uid,
        existing_doc.content = legal_doc.content
        existing_doc.file_name = legal_doc.file_name
        existing_doc.chunks = legal_doc.chunks
        existing_doc.is_lock = legal_doc.is_lock,
        existing_doc.is_private = legal_doc.is_private,
        existing_doc.is_deleted = legal_doc.is_deleted,
        # Include additional fields from metadata_dict
        for key, value in metadata_dict.items():
            setattr(existing_doc, key, value)

        existing_doc.save()
    else:
        # Save the new document
        legal_doc.save()

    return legal_doc.uid

def inject_document(
    user,
    file_name,
    content=None,
    metadata=None,
    is_lock=False,
    is_private=True,
    is_deleted=False,
):

    url = ""
    file_size = ""
    # Remove spaces from the file name and replace with underscores

    # Append _<datetime> to the file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cleaned_file_name = f"{file_name}_{timestamp}"

    document = Document.objects.create(
        owner=user, is_lock=is_lock, is_private=is_private, is_deleted=is_deleted
    )
    document_version = DocumentVersion.objects.create(
        url=url,
        message="New Document",
        file_name=cleaned_file_name,
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
    inject_to_els(document_version.uid, content)
    # Log the action
    log_action(
        user=user,
        document=document,
        version=document_version,
        action="CREATE",
        description=f"Document {file_name} created.",
    )

    response_data = {
        "document": {**model_to_dict(document), "uid": document.uid},
        "versions": {
            **model_to_dict(document_version),
            "uid": document_version.uid,
            "metadata": created_metadata,
        },
    }
    return JsonResponse(response_data)

