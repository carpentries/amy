from typing import Any, cast

from django import template
from django.http import HttpRequest

register = template.Library()


@register.inclusion_tag("pagination.html", takes_context=True)
def pagination(context: dict[str, Any], objects: Any) -> dict[str, Any]:
    # needed in set_page_query that's only called from 'pagination.html'
    request = context["request"]
    return {"objects": objects, "request": request}


@register.simple_tag(takes_context=True)
def set_page_query(context: dict[str, Any], page: Any) -> str:
    query = cast(HttpRequest, context["request"]).GET.copy()
    query["page"] = str(page)
    return query.urlencode()
