import logging

from django.http import HttpRequest, JsonResponse

from utils.exceptions import BaseException, ExceptionQueue


LOGGER = logging.getLogger("API")


def exception_handler(request: HttpRequest, exception: Exception):
    errors_queue = ExceptionQueue()

    if isinstance(exception, (BaseException, ExceptionQueue)):
        LOGGER.error(f"> Error: {exception}")
        errors_queue += exception
    else:
        LOGGER.exception(exception)
        errors_queue += BaseException(message=str(exception))

    return JsonResponse(data=errors_queue.to_response())
