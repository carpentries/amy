from typing import cast

from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from django.db.models.fields.related import RelatedField
from django.utils.safestring import SafeString, mark_safe
from reversion.models import Version
from reversion_compare.helpers import SEMANTIC, html_diff

register = template.Library()


@register.simple_tag
def semantic_diff(left: Version, right: Version, field: str) -> SafeString:
    left_txt = left.field_dict[field] or ""
    right_txt = right.field_dict[field] or ""
    return mark_safe(
        cast(
            SafeString,
            html_diff(left_txt, right_txt, cleanup=SEMANTIC),  # type: ignore[no-untyped-call]
        )
    )


@register.simple_tag
def relation_diff[M: Model](left: Version, right: Version, field: RelatedField[M]) -> SafeString:
    model = field.related_model
    field_name = field.get_attname()

    if field.many_to_one or field.one_to_one:
        # {left,right}.field_dict[field_name] is an integer or does not exist
        # Cast it to a list(empty or single itemed)
        if left.field_dict.get(field_name):
            try:
                left_PKs = [model.objects.get(pk=left.field_dict.get(field_name))]  # type: ignore[union-attr]
            except ObjectDoesNotExist:
                left_PKs = [left.field_dict.get(field_name)]
        else:
            left_PKs = []
        if right.field_dict.get(field_name):
            try:
                right_PKs = [model.objects.get(pk=right.field_dict.get(field_name))]  # type: ignore[union-attr]
            except ObjectDoesNotExist:
                right_PKs = [right.field_dict.get(field_name)]
        else:
            right_PKs = []
    else:
        left_PKs = []
        for pk in left.field_dict.get(field_name, []):
            try:
                left_PKs.append(model.objects.get(pk=pk))  # type: ignore[union-attr]
            except ObjectDoesNotExist:
                left_PKs.append(pk)
        right_PKs = []
        for pk in right.field_dict.get(field_name, []):
            try:
                right_PKs.append(model.objects.get(pk=pk))  # type: ignore[union-attr]
            except ObjectDoesNotExist:
                right_PKs.append(pk)
    # Relations that exist only in the current version
    additions = [obj for obj in right_PKs if obj not in left_PKs]
    # Relations that exist only in the previous version
    deletions = [obj for obj in left_PKs if obj not in right_PKs]
    # Relations that exist only in both versions
    consistent = [obj for obj in left_PKs if obj in right_PKs]
    add_label = "".join(
        '<a class="label label-success" href="{}">+{}</a>'.format(
            obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else "#", obj
        )
        for obj in additions
    )
    delete_label = "".join(
        '<a class="label label-danger" href="{}">-{}</a>'.format(
            obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else "#", obj
        )
        for obj in deletions
    )
    consistent_label = "".join(
        '<a class="label label-default" href="{}">{}</a>'.format(
            obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else "#", obj
        )
        for obj in consistent
    )
    return mark_safe("".join([consistent_label, add_label, delete_label]))
