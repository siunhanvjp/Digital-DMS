from django.conf import settings

from ninja_extra import NinjaExtraAPI
from ninja_extra.operation import Operation

from .exceptions import exception_handler
from .logger import _log_action
from .renderer import Renderer
from user_account.apis import UserController
from ontology.apis import OntologyController
from document_management.apis import DocumentController
from search_services.api import SearchController, OCRController, InjectController
from entry_log_management.apis import EntryLogController




api = NinjaExtraAPI(
    title=settings.PRODUCT_NAME,
    version=settings.VERSION,
    openapi_url="openapi.json",
    docs_url="docs",
#    docs='redoc',
    renderer=Renderer,  # type: ignore
)

Operation._log_action = _log_action  # type: ignore

api.register_controllers(UserController)
api.register_controllers(OntologyController)
api.register_controllers(DocumentController)
api.register_controllers(SearchController)
api.register_controllers(OCRController)
api.register_controllers(EntryLogController)
api.register_controllers(InjectController)

api.add_exception_handler(Exception, exception_handler)  # type: ignore

__all__ = ["api"]
