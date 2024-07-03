from ninja import Schema
from typing import List, Dict

class MetadataItem(Schema):
    key:str
    value:str = None

class Document(Schema):
    file_name: str
    metadata: List[Dict[str, str]] = None
    score: float
    
class SearchResult(Schema):
    documents: List[Document] = None
    broader: Dict[str, List[str]] = None
    narrower: Dict[str, List[str]] =  None
    related: Dict[str, List[str]] =  None

class OCRRespone(Schema):
    metadata: List[Dict[str, str]] = None
    