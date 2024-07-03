from typing import Any, List

from django.core.paginator import Paginator
from django.db.models import QuerySet

from ninja import Schema
from ninja.pagination import PaginationBase


class Pagination(PaginationBase):
    items_attribute: str = "content"

    class Input(Schema):
        page_size: int = 10
        page: int = 1

    class Output(Schema):
        content: List[Any]
        current_page: int
        page_size: int
        total_rows: int
        total_pages: int

    def paginate_queryset(self, queryset: QuerySet, pagination: Input, **params) -> Any:
        paginator = Paginator(queryset, pagination.page_size)

        total_pages = paginator.num_pages

        if int(total_pages) < pagination.page:
            page_number = pagination.page
            content = []
        else:
            current_page = paginator.page(pagination.page)
            page_number = current_page.number
            content = current_page.object_list

        total = paginator.count

        return {
            "content": content,
            "total_rows": total,
            "total_pages": total_pages,
            "current_page": page_number,
            "page_size": pagination.page_size,
        }
