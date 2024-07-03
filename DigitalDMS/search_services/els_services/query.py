from elasticsearch_dsl import Search, Q, SF
import json
from search_services.apps import SearchServicesConfig
# from underthesea import word_tokenize
from typing import Dict, List
from search_services.els_services.mappings import vectorize_query
import re
from django.forms.models import model_to_dict
from document_management.models import (
    Document,
    DocumentVersion,
    DocumentPermission,
    MetadataValue,
    MetadataKey,
)
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage
# print(client.synonyms.get_synonym(id="test-synonyms-set"))
DEFAULT_ELASTIC_PAGINATION_SIZE = 300

def search_semantic_metadata(key, min_score=0.8):
    # Your original query
    query = Search(index=settings.METADATA_INDEX).extra(size=3, min_score=min_score).knn(
        field="key_embedding",
        k=3,
        num_candidates=10,
        query_vector=vectorize_query(key)
    )

    # Executing the query
    response = query.execute()

    # Retrieving the top result (since k=1)
    top_result = [hit.key for hit in response.hits]
    return top_result
    

class QueryHandler: 
    DEFAULT_ELASTIC_PAGINATION_SIZE = settings.DEFAULT_ELASTIC_PAGINATION_SIZE
    def __init__(self, payload, suggestion):
        self.search_query = payload.original_query
        self.method = payload.method # full-text, semantic, file-name
        
        self.metadata = payload.metadata
        self.index_name = settings.SEARCH_INDEX
        
        self.suggestion = suggestion
        self.threshold = payload.threshold
        if payload.domain:
            self.keywords = self._combine_keywords(payload.broader, suggestion["related"], payload.narrower) if payload.auto else self._combine_keywords(payload.broader, payload.related, payload.narrower)
        else:
            self.keywords = None
        #self.keywords = suggestion["related"]
        self.ontology_id = payload.domain if payload.domain else None # ontology_id
        self.search_scope = payload.search_scope #
            
    def _combine_keywords(self,dict1: Dict[str, List[str]], dict2: Dict[str, List[str]], dict3: Dict[str, List[str]]) -> Dict[str, List[str]]:
        combined_dict: Dict[str, List[str]] = {}

        # Combine values for each key
        for key in set(dict1.keys()).union(dict2.keys(), dict3.keys()):
            values = dict1.get(key, []) + dict2.get(key, []) + dict3.get(key, [])
            combined_dict[key] = values

        return combined_dict

    def _preprocess_query(self, query):
        # Define a list of special characters to escape
        special_characters = ['+', '-', '=', '&&', '||', '>', '<', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/']

        # Escape special characters with \
        escaped_query = re.sub(r'([{}])'.format(re.escape(''.join(special_characters))), r'\\\1', query)

        # Remove < and >
        cleaned_query = re.sub(r'[<>]', '', escaped_query)

        return cleaned_query
        
    def _pretty_results(self, response):
        results = []

        for hit in response:
            results.append(hit.uid)
        return results
    
    def _refine_query(self):
        refined_query = self._preprocess_query(self.search_query)
        for key, values in self.keywords.items():
             # A B C A -> A + B C + A -> (A OR D) + B C + (A OR D)
            combined_values = ' OR '.join([f"\"{value}\"" for value in values])
            refined_query = refined_query.replace(key, f"(\"{key}\" OR {combined_values})")
            # combined_values = '"' + '" OR "'.join(values) + '"'
            # refined_query = refined_query.replace(key, f"(\"{key}\" OR {combined_values})")

        return refined_query
    
    @staticmethod
    def _build_filter_query(metadata_conditions, init=False): #return a list of terms
        if init:
            is_delete_filter = Q("term", is_deleted=False)
            query = [is_delete_filter] # -> to return a list of query object
        else:
            query = []
        for condition in metadata_conditions:
            if "$and" in condition:
                and_query = Q("bool", must=QueryHandler._build_filter_query(condition["$and"]))
                query.append(and_query)
            elif "$or" in condition:
                or_query = Q("bool", should=QueryHandler._build_filter_query(condition["$or"]), minimum_should_match=1)
                query.append(or_query)
            elif "$not" in condition:
                not_query = Q("bool", must_not=Q("match_phrase", **{condition["$not"]["key"]: condition["$not"]["value"]}))
                query.append(not_query)
            else:
                key = condition["key"]
                value = condition["value"]
                term_query = Q("match_phrase", **{key: value})
                query.append(term_query)

        return query
    
    def search_documents(self):
        search_obj = Search(index=self.index_name).extra(size=self.DEFAULT_ELASTIC_PAGINATION_SIZE, min_score=self.threshold)
        filter_query = self._build_filter_query(self.metadata, init=True)
        
        if self.method == "semantic":
            query = search_obj.knn(
                field="chunks.chunk_embedding", # replace this one 
                k=self.DEFAULT_ELASTIC_PAGINATION_SIZE,
                num_candidates=int(self.DEFAULT_ELASTIC_PAGINATION_SIZE*1.5),
                query_vector=vectorize_query(self.search_query),
                filter=filter_query
            )
        else:
            if self.method == "file-name":
                search_query = Q('wildcard', file_name=f"*{self.search_query}*")
            elif self.method == "full-text":
                if not self.ontology_id:
                    search_query = Q('multi_match', query=self.search_query, fields=[])
                else:
                    refined_query = self._refine_query()
                    search_query =Q('query_string', query=refined_query)
                    
            if self.search_query:
                print("Search query: ", search_query.to_dict())
                combined_query = Q('bool', must=search_query, filter=filter_query)
            else:
                combined_query = Q('bool', filter=filter_query)
            
            query = search_obj.query(combined_query)
        query = query.source(["uid"])
        
        print("Query: ", query.to_dict())
        print(self._pretty_results(query))
        return query
        # return self._pretty_results(response)
        
    def _get_all_search_results(self, page, page_size, uid_result):
        page = int(page)
        page_size = int(page_size)
        public_documents = Document.objects.filter(
            is_private=False, is_deleted=False, uid__in=uid_result
        )
        len_doc = public_documents.count()
        print("Total doc", len_doc)
        
        exdict = {str(doc.uid): doc for doc in public_documents} # rearrange
        documents = [exdict[e]for e in uid_result if exdict.get(e, None)]
        
        paginated_documents, total_pages = self._paginate_documents(
            documents, page, page_size
        )

        matrix = []
        for doc in paginated_documents:
            doc_dict = self._get_document_dict(doc)
            doc_dict["versions"] = self._get_versions_info(
                doc
            )  # Pass Django object here
            matrix.append(doc_dict)

        return {
            "documents": matrix,
            "current_page": page,
            "total_pages": total_pages,
            "page_size": page_size,
            "total_items": public_documents.count(),
        }
        
    def _get_my_search_results(self, page, page_size, uid_result, user, is_private=True):
        page = int(page)
        page_size = int(page_size)
        query_params = {"owner": user, "is_private": is_private, "is_deleted": False}
        public_documents = Document.objects.filter(
            **query_params, uid__in=uid_result
        )
        len_doc = public_documents.count()
        print("Total doc", len_doc)
        
        exdict = {str(doc.uid): doc for doc in public_documents} # rearrange
        documents = [exdict[e]for e in uid_result if exdict.get(e, None)]
        
        paginated_documents, total_pages = self._paginate_documents(
            documents, page, page_size
        )

        matrix = []
        for doc in paginated_documents:
            doc_dict = self._get_document_dict(doc)
            doc_dict["versions"] = self._get_versions_info(
                doc
            )  # Pass Django object here
            matrix.append(doc_dict)

        return {
            "documents": matrix,
            "current_page": page,
            "total_pages": total_pages,
            "page_size": page_size,
            "total_items": public_documents.count(),
        }
        
    def _get_shared_search_results(self, page, page_size, uid_result, user):
        page = int(page)
        page_size = int(page_size)
        document_permissions = (
            DocumentPermission.objects.filter(user=user)
            .exclude(document__owner=user)
            .select_related("document")
        )
        document_ids = document_permissions.values_list("document_id", flat=True)
        shared_documents = Document.objects.filter(
            id__in=document_ids, is_deleted=False
        )
        # public_documents = Document.objects.filter(
        #     is_private=False, is_deleted=False
        # ).exclude(owner=user)
        documents = shared_documents
        
        len_doc = documents.count()
        print("Total doc", len_doc)
        
        exdict = {str(doc.uid): doc for doc in documents} # rearrange
        documents = [exdict[e]for e in uid_result if exdict.get(e, None)]
        
        print("Total result", len(documents))
        
        paginated_documents, total_pages = self._paginate_documents(
            documents, page, page_size
        )

        matrix = []
        for doc in paginated_documents:
            doc_dict = self._get_document_dict(doc)
            doc_dict["versions"] = self._get_versions_info(
                doc
            )  # Pass Django object here
            matrix.append(doc_dict)

        return {
            "documents": matrix,
            "current_page": page,
            "total_pages": total_pages,
            "page_size": page_size,
            "total_items": shared_documents.count(),
        }
       
    def get_search_results(self, page, page_size, user=None, is_private=True, is_deleted=False):
        s = self.search_documents() #->build search query
        s = self._pretty_results(s) #->execute search query
        
        if self.search_scope == "my":
           return self._get_my_search_results(page=page, page_size=page_size, uid_result=s,
                                              user=user, is_private=is_private)
        if self.search_scope == "company":
            return self._get_all_search_results(page=page, page_size=page_size, uid_result=s)
        if self.search_scope == "shared": 
            return self._get_shared_search_results(page=page, page_size=page_size, uid_result=s, user=user)
        return {}
        
    def _get_document_dict(self, document):
        document_dict = model_to_dict(document)
        document_dict["uid"] = str(document.uid)
        document_dict["owner"] = self._get_owner_info(document.owner)
        document_dict["created_date"] = str(document.create_date)
        document_dict["updated_date"] = str(document.updated_date)
        return document_dict
    
    def _get_owner_info(self, owner):
        return {
            "first_name": owner.first_name,
            "last_name": owner.last_name,
            "username": owner.username,
            "email": owner.email,
        }
    
    def _get_versions_info(self, document):
        versions_list = []
        document_versions = DocumentVersion.objects.filter(document=document).order_by(
            "-create_date"
        )
        for dv in document_versions:
            version_info = model_to_dict(dv)
            version_info["uid"] = str(dv.uid)
            version_info["user"] = self._get_owner_info(dv.user)
            version_info["created_date"] = str(dv.create_date)
            version_info["updated_date"] = str(dv.updated_date)
            metadata_values = MetadataValue.objects.filter(document_version=dv)
            metadata_list = [{mv.key.key: mv.value} for mv in metadata_values]
            version_info["metadata"] = metadata_list
            versions_list.append(version_info)
        return versions_list
    
    def _paginate_documents(self, documents, page, page_size):
        paginator = Paginator(documents, page_size)
        try:
            paginated_documents = paginator.page(page)
        except EmptyPage:
            paginated_documents = []
        return paginated_documents, paginator.num_pages



