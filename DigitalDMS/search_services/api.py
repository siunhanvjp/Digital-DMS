from ninja_extra import api_controller, http_get, http_post, http_put, http_delete
from typing import List
from ninja import UploadedFile, File
from .schema.payload import SearchRequest, OCRRequest, InjectDocumentRequest
import json
from .els_services.query import QueryHandler
from ontology.apis.ontology import get_suggestion
from .services import ocr_docs, generate_metadata, convert_to_custom_format, inject_document
from ontology.apis.ontology import get_suggestion_new
from router.authenticate import AuthBearer
from typing import Optional

@api_controller('/search', tags=["Search Documents"])
class SearchController:
    @http_post('', auth=AuthBearer())
    def search_docs(self, request, payload: SearchRequest, page: Optional[int] = 1, page_size: Optional[int] = 10):
        # search_scope: company, my, shared
        default_suggestion = {
            "broader": [],
            "related": [],
            "narrower": []
        }
        suggestion = (get_suggestion_new(ontologyId=payload.domain, original_query=payload.original_query)) if (payload.domain and payload.domain != "") else default_suggestion
        
        handler = QueryHandler(payload, suggestion)
        # print(json.dumps(suggestion, indent=4, ensure_ascii=False))
        documents = handler.get_search_results(page=page, page_size=page_size, user=request.user)
        
        search_result = {"search_result": documents}
        
        search_result.update(suggestion)
        
        return search_result

  
@api_controller('/ocr', tags=["OCR"])
class OCRController:
    
    @http_post('', auth=AuthBearer())
    # only purpose is to read the first page and return metadata
    def extract_metadata(self, request, pdf_file: UploadedFile):
        
        if pdf_file.content_type != 'application/pdf':
            return {}
        try:
            text = ocr_docs(pdf_file.read(), pages="1")
            metadata = generate_metadata(text)
        # print(metadata)
        # metadata = generate_metadata(raw_text)
            return {
                'metadata': convert_to_custom_format(metadata),
                'content': text
            }
        except Exception as e:
            print(e)
            return {}

@api_controller('/inject', tags=["Inject Documents"])
class InjectController:
    @http_post('', auth=AuthBearer())
    def inject_data(self, request, data: Optional[InjectDocumentRequest] = None):
        """
        {
            "metadata": {}
            "content": "str"
            "file_name" "abc"
        }
        """
        return inject_document(request.user, data.file_name, data.content, convert_to_custom_format(data.metadata))