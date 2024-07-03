# THIS IS A SCRIPT, ONLY RUN ONCE
from elasticsearch_dsl import (
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
import google.generativeai as genai
import os
import random
from elasticsearch import Elasticsearch
from django.conf import settings
# # Initialize Elasticsearch client
# ELASTIC_PASSWORD = "OxN4F5Bwg1O7ZAtLXc5V"
# # test-synonyms-set
# print("called")
# # Set the connection alias for Elasticsearch DSL
# connections.create_connection(alias='default', hosts=["http://localhost:9200"], basic_auth=("elastic", ELASTIC_PASSWORD))


# Define your document type with mappings

class ContentChunk(InnerDoc):
    chunk_content=Keyword()
    chunk_embedding=DenseVector(dims=768, index=True, similarity='cosine')
    
class MetadataKeyDoc(Document):
    key = Keyword()
    key_embedding = DenseVector(dims=768, index=True, similarity='cosine')
    
    class Meta:
        dynamic = MetaField("true")

    class Index:
        name = settings.METADATA_INDEX
        
    def __init__(self, *args, **kwargs):
        if not MetadataKeyDoc._index.exists():
            MetadataKeyDoc._index.delete(ignore_unavailable=True)
            MetadataKeyDoc.init()
        kwargs['key_embedding'] = get_openai_embedding(kwargs['key'])
        super().__init__(*args, **kwargs)
        

class LegalDocument(Document):
    # file specific field
    uid = Keyword() #-> belong to document
    version_uid = Keyword() #->belong to a version
    file_name  = Keyword()
    # file optional field
    content  = Text()
    # law_id = Keyword()
    # title = Text()
    # summary = Text()
    # tag = Text()
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


def get_gemini_embedding(content, model="models/text-embedding-004"):
    result = genai.embed_content(
    model=model,
    content=content,
    task_type="SEMANTIC_SIMILARITY")
    return result["embedding"]

def get_openai_embedding(content: str, model="text-embedding-3-large"):
    
    from openai import OpenAI
    client = OpenAI()  

    content = content.replace("\n", " ")
    result = client.embeddings.create(input = [content],
                                   model=model,
                                   dimensions=768).data[0].embedding
    return result

def vectorize_query(query):
    return get_openai_embedding(query)
        
        