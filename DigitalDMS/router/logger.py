import logging
from typing import Any, Callable, Optional

from django.http import HttpRequest

from ninja_extra.logger import request_logger


LOGGER = logging.getLogger("API")


def _log_action(
    self,
    logger: Callable[..., Any],
    request: HttpRequest,
    duration: Optional[float] = None,
    ex: Optional[Exception] = None,
    **kwargs: Any,
) -> None:
    try:
        if hasattr(self.view_func, "get_route_function"):
            route_function = self.view_func.get_route_function()  # type:ignore
            api_controller = route_function.get_api_controller()

            LOGGER.debug(f"> Controller: {api_controller.controller_class.__name__}")
        LOGGER.debug(f"> Function: {self.view_func.__name__}")

    except Exception as log_ex:
        request_logger.debug(log_ex)


__all__ = ["_log_action"]
