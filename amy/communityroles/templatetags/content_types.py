from typing import List

from django import template
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet

register = template.Library()


@register.simple_tag
def get_content_type_objects_by_ids(
    content_type: ContentType, object_ids: List[int]
) -> QuerySet:
    return content_type.model_class()._base_manager.filter(id__in=object_ids)
