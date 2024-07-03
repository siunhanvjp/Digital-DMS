from ninja import File
from ninja.files import UploadedFile
from ninja_extra import api_controller, http_get, http_post, http_put
from ninja.files import UploadedFile

from ..schema.payload import (
    DocumentRequest,
    DocumentPermissionGrant,
    DocumentPermissionUnGrant,
    KeyRequest
)
from router.authenticate import AuthBearer
from ..models.document import Document, DocumentPermission
from ..services.document import DocumentService
from typing import Optional
from django.http import QueryDict
from search_services.tasks import delete_document_els

@api_controller(prefix_or_class="documents", tags=["Document"])
class DocumentController:
    @http_get("/matrix", auth=AuthBearer())
    def get_all_document(
        self, request, page: Optional[int] = 1, page_size: Optional[int] = 10
    ):
        # Call the get_all_document function with pagination parameters
        return DocumentService().get_all_document(page=page, page_size=page_size)

    @http_get("/matrix/me", auth=AuthBearer())
    def get_my_document(
        self,
        request,
        is_private: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 10,
    ):
        return DocumentService().get_my_document(
            user=request.user,
            is_private=is_private,
            is_deleted=is_deleted,
            page=page,
            page_size=page_size,
        )

    @http_get("/matrix/shared", auth=AuthBearer())
    def get_shared_document(
        self, request, page: Optional[int] = 1, page_size: Optional[int] = 10
    ):
        return DocumentService().get_shared_document(
            user=request.user, page=page, page_size=page_size
        )

    @http_get("/detail/{uid}", auth=AuthBearer())
    def get_document_detail(
        self,
        request,
        uid,
    ):
        return DocumentService().get_document(user=request.user, uid=uid)

    @http_post("/create", auth=AuthBearer())
    def create(
        self,
        request,
        data: Optional[DocumentRequest] = None,
        files: Optional[UploadedFile] = File(None),
    ):
        if data != None:
            return DocumentService().create_document(
                user=request.user, metadata=data.metadata, files=files
            )
        else:
            return DocumentService().create_document(user=request.user, files=files)

    @http_post("/update/{uid}", auth=AuthBearer())
    def update_file(
        self,
        request,
        uid,
        data: Optional[DocumentRequest] = None,
        files: Optional[UploadedFile] = File(None),
    ):
        if files != None:
            return DocumentService().update_document_with_file(
                user=request.user,
                uid=uid,
                metadata=data.metadata,
                files=files,
                message=data.message,
            )
        else:
            return DocumentService().update_document_with_metadata(
                user=request.user,
                uid=uid,
                metadata=data.metadata,
                message=data.message,
            )

    @http_post("/delete/forever/{uid}", auth=AuthBearer())
    def delete_forever(self, request, uid):
        return DocumentService().delete_document(user=request.user, document_id=uid)

    @http_post("/grant", auth=AuthBearer())
    def grant_permission(
        self,
        request,
        data: DocumentPermissionGrant,
    ):
        return DocumentService().grant_permission(
            user_email=data.email,
            document_uid=data.document_uid,
            permission=data.permission,
        )

    @http_post("/ungrant", auth=AuthBearer())
    def delete_permission(
        self,
        request,
        data: DocumentPermissionUnGrant,
    ):
        return DocumentService().delete_permission(
            user_email=data.email,
            document_uid=data.document_uid,
        )

    @http_post("/delete/{uid}", auth=AuthBearer())
    def delete(self, request, uid):
        document = Document.get_by_uid(uid=uid)
        if (
            DocumentPermission.has_permission(
                user=request.user, document=document, permission="EDIT"
            )
            == False
        ):
            return {"message": "User do not have permission to delete this document"}
        delete_document_els.delay(uid_value=uid, is_soft=True)
        document.is_deleted = True
        document.save()
        return DocumentService().get_document(user=request.user, uid=uid)

    @http_post("/restore/{uid}", auth=AuthBearer())
    def restore(self, request, uid):
        document = Document.get_by_uid(uid=uid)
        if (
            DocumentPermission.has_permission(
                user=request.user, document=document, permission="EDIT"
            )
            == False
        ):
            return {"message": "User do not have permission to restore this document"}
        document.is_deleted = False
        document.save()
        return DocumentService().get_document(user=request.user, uid=uid)

    @http_post("/lock/{uid}", auth=AuthBearer())
    def lock(self, request, uid):
        document = Document.get_by_uid(uid=uid)
        if (
            DocumentPermission.has_permission(
                user=request.user, document=document, permission="EDIT"
            )
            == False
        ):
            return {"message": "User do not have permission to lock this document"}
        document.is_lock = True
        document.save()
        return DocumentService().get_document(user=request.user, uid=uid)

    @http_post("/unlock/{uid}", auth=AuthBearer())
    def unlock(self, request, uid):
        document = Document.get_by_uid(uid=uid)
        if (
            DocumentPermission.has_permission(
                user=request.user, document=document, permission="EDIT"
            )
            == False
        ):
            return {"message": "User do not have permission to unlock this document"}
        document.is_lock = False
        document.save()
        return DocumentService().get_document(user=request.user, uid=uid)

    @http_post("/private/{uid}", auth=AuthBearer())
    def private(self, request, uid):
        document = Document.get_by_uid(uid=uid)
        if (
            DocumentPermission.has_permission(
                user=request.user, document=document, permission="EDIT"
            )
            == False
        ):
            return {
                "message": "User do not have permission to set private this document"
            }
        document.is_private = True
        document.save()
        return DocumentService().get_document(user=request.user, uid=uid)

    @http_post("/public/{uid}", auth=AuthBearer())
    def public(self, request, uid):
        document = Document.get_by_uid(uid=uid)
        if (
            DocumentPermission.has_permission(
                user=request.user, document=document, permission="EDIT"
            )
            == False
        ):
            return {
                "message": "User do not have permission to set public this document"
            }
        document.is_private = False
        document.save()
        return DocumentService().get_document(user=request.user, uid=uid)

    @http_post("/restore/{document_uid}/version/{version_uid}", auth=AuthBearer())
    def restore_version(self, request, document_uid, version_uid):
        return DocumentService().restore_version(
            user=request.user, document_uid=document_uid, version_uid=version_uid
        )

    @http_get("/live-search-metadata", auth=AuthBearer())
    def live_search_metadata(self, request):
        query = request.GET.get("query", "")
        return DocumentService().live_search_metadata(query)
    
    @http_post("/live-search-semantic-metadata", auth=AuthBearer())
    def live_search_semantic_metadata(self, request, query:KeyRequest):
        return DocumentService().live_search_semantic_metadata(query)
