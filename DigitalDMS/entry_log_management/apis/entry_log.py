from django.http import JsonResponse
from ninja import File
from ninja.files import UploadedFile
from ninja_extra import api_controller, http_get, http_post, http_put
from ninja.files import UploadedFile


from router.authenticate import AuthBearer
from typing import Optional
from entry_log_management.models import EntryLogs
from document_management.services.document import DocumentService


@api_controller(prefix_or_class="logs", tags=["Logs"])
class EntryLogController:
    @http_get("/matrix/{document_uid}", auth=AuthBearer())
    def get_entry_logs_by_document_uid(
        self,
        request,
        document_uid: str,
        page: Optional[int] = 1,
        page_size: Optional[int] = 10,
    ):
        try:
            entry_logs = EntryLogs.objects.filter(document__uid=document_uid).order_by(
                "-time"
            )
            total_logs = entry_logs.count()
            entry_logs = entry_logs[(page - 1) * page_size : page * page_size]

            logs_data = [
                {
                    "uid": log.uid,
                    "modified_by": DocumentService()._get_owner_info(log.modified_by),
                    "document_uid": DocumentService()._get_document_dict(log.document),
                    "document_version_uid": (
                        log.document_version.uid if log.document_version else None
                    ),
                    "action": log.action,
                    "description": log.description,
                    "time": log.time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for log in entry_logs
            ]

            return JsonResponse({"logs": logs_data, "total_logs": total_logs})
        except EntryLogs.DoesNotExist:
            return JsonResponse(
                {"error": "Entry logs for the specified document UID not found."},
                status=404,
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
