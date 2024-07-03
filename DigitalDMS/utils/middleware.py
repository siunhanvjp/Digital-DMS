import logging
import time
from datetime import datetime

from django.db import connection
from django.http import JsonResponse


LOGGER = logging.getLogger("API")


class ResponseHandleWiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_time = time.time()
        started_connection_queries = len(connection.queries)

        LOGGER.info("---------------------------------------------------------------")

        response = self.get_response(request)

        ended_time = time.time()
        ended_connection_queries = len(connection.queries)

        LOGGER.debug(f"> Response: {response.status_code} {response.reason_phrase}")
        LOGGER.debug(f"> Authenticator: {request.user}")
        LOGGER.debug(f"> Running time: {ended_time - started_time}")
        LOGGER.debug(f"> Number of queries: {ended_connection_queries - started_connection_queries}")

        if response.status_code == 401:
            return JsonResponse(
                {
                    "data": None,
                    "errors": [],
                    "error_code": response.status_code,
                    "message_code": "EXPIRED_SESSION",
                    "message": "Session has expired",
                    "current_time": datetime.now(),
                }
            )

        if response.status_code == 403:
            message = response.data.get("detail", "Permission denied")
            return JsonResponse(
                {
                    "data": None,
                    "errors": [],
                    "error_code": 401,  # For returning 401 to frontend
                    "message_code": "PERMISSION_DENIED",
                    "message": message or "Permission denied",
                    "current_time": datetime.now(),
                }
            )

        if response.status_code == 404 and response.reason_phrase == "Not Found":
            return JsonResponse(
                {
                    "data": None,
                    "errors": [],
                    "error_code": response.status_code,
                    "message_code": "PAGE_NOT_FOUND",
                    "message": "Page not found",
                    "current_time": datetime.now(),
                }
            )

        if response.status_code == 405:
            return JsonResponse(
                {
                    "data": None,
                    "errors": [],
                    "error_code": response.status_code,
                    "message_code": "METHOD_NOT_ALLOWED",
                    "message": response.data["detail"] if hasattr(response, "data") else "Method not allowed",
                    "current_time": datetime.now(),
                }
            )

        if response.status_code == 302:
            # Handle 302 status_code
            pass
        elif response.status_code != 200:
            return JsonResponse(
                {
                    "data": None,
                    "errors": [],
                    "error_code": response.status_code,
                    "message_code": "CONTACT_ADMIN_FOR_SUPPORT",
                    "message": "Contact admin for support",
                    "current_time": datetime.now(),
                }
            )

        return response
