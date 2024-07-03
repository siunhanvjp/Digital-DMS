from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage

from typing import Optional
from datetime import datetime
from math import ceil

import boto3
import requests
import io
from ..models.document import (
    Document,
    DocumentVersion,
    DocumentPermission,
    MetadataValue,
    MetadataKey,
)
from user_account.models.user import User
from search_services.tasks import upload_to_els, delete_document_els, sync_metadata
from search_services.els_services.query import search_semantic_metadata

import boto3
from django.http import JsonResponse
from django.forms.models import model_to_dict
import requests
from entry_log_management.models.entry_log import EntryLogs
from utils.enums.document import DocumentActionEnum, DocumentPermissionEnum
from utils.exceptions.exceptions import NotFound, ValidationError
from unidecode import unidecode
from botocore.exceptions import ClientError
import pickle


class DocumentService:
    def __init__(self):
        pass

    def log_action(self, user, document, version, action, description):
        EntryLogs.objects.create(
            modified_by=user,
            document=document,
            document_version=version,
            action=action,
            description=description,
        )

    # =====CREATE AND UPDATE DOCUMENT=====

    def s3_upload(self, path_key, files):
        s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
        response = s3.put_object(
            Body=files,
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=path_key,
            ContentType="application/pdf",
            ContentDisposition="inline",
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            object_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{path_key}"
            return object_url
        else:
            return None

    def s3_presigned_upload(self, path_key, files):
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        response = s3_client.generate_presigned_post(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=path_key, ExpiresIn=30
        )
        r = requests.post(response["url"], data=response["fields"], files=files)
        return r

    def create_document(
        self,
        user,
        files=None,
        metadata=None,
        is_lock=False,
        is_private=True,
        is_deleted=False,
    ):
        folder_path = f"{user.username}/documents/"
        url = ""
        file_name = ""
        file_size = ""
        if files:
            file_size = files.size
            # Remove spaces from the file name and replace with underscores
            cleaned_file_name = files.name.replace(" ", "_")

            # Append _<datetime> to the file name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{cleaned_file_name}_{timestamp}"

            file_path = folder_path + cleaned_file_name
            pdf_bytes = files.read()
            if settings.ALLOW_UPLOAD == "True":
                s3_file = io.BytesIO(pdf_bytes)
                self.s3_upload(file_path, s3_file)
            url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{file_path}"

        document = Document.objects.create(
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
            created_metadata = self._create_metadata(metadata, document_version)

        ### UPLOAD TO ELS ###
        if files:
            els_file = io.BytesIO(pdf_bytes)
            upload_to_els.delay(
                document_version.uid, pickle.dumps(els_file.read()), skip_OCR=False
            )

        # Log the action
        self.log_action(
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

    def _create_metadata(self, metadata, document_version):
        created_metadata = []
        keys_to_sync = []
        for item in metadata:
            for key, value in item.items():
                metadata_key, created = MetadataKey.objects.get_or_create(key=key)
                if created: 
                    keys_to_sync.append(key)
                metadata_value = MetadataValue.objects.create(
                    value=value, key=metadata_key, document_version=document_version
                )
                created_metadata.append({key: value})
        sync_metadata.delay(keys_to_sync)
        return created_metadata

    def update_document_with_file(self, user, uid, files, message, metadata=None):
        folder_path = f"{user.username}/documents/"
        document = Document.get_by_uid(uid=uid)
        if not DocumentPermission.has_permission(
            user=user, document=document, permission="EDIT"
        ):
            return {"message": "User does not have permission to edit this document"}

        latest_document_version = DocumentVersion.get_latest_version(document=document)
        # Remove spaces from the file name and replace with underscores
        cleaned_file_name = files.name.replace(" ", "_")

        # Append _<datetime> to the file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cleaned_file_name = f"{cleaned_file_name}_{timestamp}"

        file_path = folder_path + cleaned_file_name
        pdf_bytes = files.read()
        if settings.ALLOW_UPLOAD == "True":
            s3_file = io.BytesIO(pdf_bytes)
            self.s3_upload(file_path, s3_file)
        url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{file_path}"
        document_version = DocumentVersion.objects.create(
            url=url,
            message=message,
            file_name=files.name,
            file_size=files.size,
            user=user,
            document=document,
        )
        latest_document_version.next_version = document_version
        latest_document_version.save()

        created_metadata = []
        if metadata:
            created_metadata = self._create_metadata(metadata, document_version)

        ### UPLOAD TO ELS ###
        els_file = io.BytesIO(pdf_bytes)
        upload_to_els.delay(
            document_version.uid, pickle.dumps(els_file.read()), skip_OCR=False
        )

        # Log the action
        self.log_action(
            user=user,
            document=document,
            version=document_version,
            action="UPDATE",
            description=f"Document updated with a new file {cleaned_file_name}.",
        )

        version_data = self._get_versions_info(document)
        response_data = {"document": model_to_dict(document), "versions": version_data}
        return JsonResponse(response_data)

    def update_document_with_metadata(self, user, uid, metadata, message):
        document = Document.get_by_uid(uid=uid)
        if not DocumentPermission.has_permission(
            user=user, document=document, permission="EDIT"
        ):
            return {"message": "User does not have permission to edit this document"}

        latest_document_version = DocumentVersion.get_latest_version(document=document)
        document_version = DocumentVersion.objects.create(
            url=latest_document_version.url,
            message=message,
            file_name=latest_document_version.file_name,
            file_size=latest_document_version.file_size,
            user=user,
            document=document,
            content=latest_document_version.content,
        )
        latest_document_version.next_version = document_version
        latest_document_version.save()

        created_metadata = self._create_metadata(metadata, document_version)

        ### UPLOAD TO ELS ###

        upload_to_els.delay(document_version.uid, skip_OCR=True)

        # Log the action
        self.log_action(
            user=user,
            document=document,
            version=document_version,
            action="UPDATE",
            description="Document metadata updated.",
        )

        version_data = self._get_versions_info(document)
        response_data = {"document": model_to_dict(document), "versions": version_data}
        return JsonResponse(response_data)

    def delete_document(self, user, document_id):
        try:
            document = Document.objects.get(uid=document_id, owner=user)
        except Document.DoesNotExist:
            return JsonResponse(
                {"error": "Document not found or you don't have permission to delete."},
                status=404,
            )

        #### SYNC WITH ELS ####
        delete_document_els.delay(uid_value=document_id)  # hard-delete

        document_versions = DocumentVersion.objects.filter(document=document)
        s3 = boto3.client("s3")

        for version in document_versions:
            try:
                if version.url:
                    s3.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=version.url
                    )
            except ClientError as e:
                # Log error or handle as needed
                print(f"Error deleting object from S3: {e}")

        document_versions.delete()

        DocumentPermission.objects.filter(document=document).delete()

        document.delete()

        return JsonResponse({"message": "Document deleted successfully."})

    # =====GRANT AND DELETE PERMISSIONS=====

    def grant_permission(self, user_email, document_uid, permission):
        user = User.get_user_by_email(email=user_email)
        document = Document.get_by_uid(uid=document_uid)
        document_permission, _ = DocumentPermission.objects.get_or_create(
            user=user, document=document, defaults={"permission": permission}
        )
        if document_permission.permission != permission:
            document_permission.permission = permission
            document_permission.save()

            # Log the action
            self.log_action(
                user=user,
                document=document,
                version=DocumentVersion.get_latest_version(document=document),
                action="PERMISSION_GRANTED",
                description=f"User {user.email} is granted permission to {permission} this document.",
            )

            return {"message": "Permission updated successfully"}
        else:
            return {"message": f"Permission is already set to {permission}"}

    def delete_permission(self, user_email, document_uid):
        user = User.get_user_by_email(email=user_email)
        document = Document.get_by_uid(uid=document_uid)
        try:
            document_permission = DocumentPermission.objects.get(
                user=user, document=document
            )
            document_permission.delete()

            # Log the action
            self.log_action(
                user=user,
                document=document,
                version=DocumentVersion.get_latest_version(document=document),
                action="PERMISSION_REMOVE",
                description=f"User {user.email} permission to this document has been removed.",
            )

            return {"message": "Permission record deleted successfully"}
        except DocumentPermission.DoesNotExist:
            return {"message": "Permission record not found"}

    # =====GET DOCUMENTS=====

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

    def get_my_document(
        self, user, page=1, page_size=10, is_private=None, is_deleted=None
    ):
        page = int(page)
        page_size = int(page_size)
        query_params = {"owner": user, "is_deleted": False}
        if is_private is not None:
            query_params["is_private"] = is_private
        if is_deleted is not None:
            query_params["is_deleted"] = is_deleted
        documents = Document.objects.filter(**query_params).order_by("-create_date")

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
            "total_items": documents.count(),
        }

    def get_shared_document(self, user, page=1, page_size=10):
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
        documents = shared_documents.order_by("-create_date")
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
            "total_items": documents.count(),
        }

    def get_all_document(self, page=1, page_size=10):
        page = int(page)
        page_size = int(page_size)
        public_documents = Document.objects.filter(
            is_private=False, is_deleted=False
        ).order_by("-create_date")
        paginated_documents, total_pages = self._paginate_documents(
            public_documents, page, page_size
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

    def get_document(self, user, uid):
        try:
            document = Document.objects.get(uid=uid)
            document_dict = self._get_document_dict(document)
            document_dict["versions"] = self._get_versions_info(document)
            document_dict["is_owner"] = document.owner == user
            document_dict["permission"] = (
                DocumentPermission.objects.filter(user=user, document=document)
                .first()
                .permission
                if DocumentPermission.objects.filter(
                    user=user, document=document
                ).first()
                else None
            )
            document_dict["users_with_permission"] = [
                {
                    "uid": str(doc_permission.user.uid),
                    "first_name": doc_permission.user.first_name,
                    "last_name": doc_permission.user.last_name,
                    "username": doc_permission.user.username,
                    "email": doc_permission.user.email,
                    "permission": doc_permission.permission,
                }
                for doc_permission in DocumentPermission.objects.filter(
                    document=document
                )
            ]
            return document_dict
        except Document.DoesNotExist:
            return {"message": "No document found"}

    # =====GET VERSIONS=====

    def restore_version(self, user, document_uid, version_uid):
        try:
            document = Document.get_by_uid(uid=document_uid)
            if not (
                DocumentPermission.has_permission(
                    user=user, document=document, permission="EDIT"
                )
                or document.is_private == False
            ):
                return {
                    "message": "User does not have permission to restore document versions"
                }

            latest_document_version = DocumentVersion.get_latest_version(
                document=document
            )

            chosen_version = DocumentVersion.objects.get(
                uid=version_uid, document=document
            )

            # Create a copy of the chosen version
            copied_version = DocumentVersion.objects.create(
                url=chosen_version.url,
                message=chosen_version.message,
                file_name=chosen_version.file_name,
                file_size=chosen_version.file_size,
                user=chosen_version.user,
                document=chosen_version.document,
                content=chosen_version.content,
            )

            metadata_values = MetadataValue.objects.filter(
                document_version=chosen_version
            )
            for metadata_value in metadata_values:
                MetadataValue.objects.create(
                    value=metadata_value.value,
                    key=metadata_value.key,
                    document_version=copied_version,
                )

            latest_document_version.next_version = copied_version
            latest_document_version.save()
            return {"message": "Document version restored successfully"}
        except (Document.DoesNotExist, DocumentVersion.DoesNotExist):
            return {"message": "No document or version found"}

    def live_search_metadata(self, query):
        query = unidecode(query).lower()
        search_results = []
        metadata_keys = MetadataKey.objects.filter(key__icontains=query)
        for metadata_key in metadata_keys:
            metadata_info = {
                "value": metadata_key.uid,
                "label": metadata_key.key,
            }
            search_results.append(metadata_info)

        return search_results
    
    def live_search_semantic_metadata(self, query):
        # pass metadata in the query, use openai_embedding generate the embedding ->
        # use the embedding to query result, get the top one
        search_results = search_semantic_metadata(query.key, query.threshold)
        metadata_keys = MetadataKey.objects.filter(key__in=search_results)
        key_list = []
        for key in metadata_keys:
            key_list.append(
                {
                "value": key.uid,
                "label": key.key,
            })
        return key_list