from django import template
from django.utils.safestring import mark_safe

from reversion.helpers import generate_patch_html

register = template.Library()


@register.simple_tag
def semantic_diff(left, right, field):
    return mark_safe(generate_patch_html(left, right, field, cleanup='semantic'))


@register.simple_tag
def relation_diff(left, right, field):
    left_relation = field.related_model.objects.get(pk=left.field_dict[field.name])
    right_relation = field.related_model.objects.get(pk=right.field_dict[field.name])
    if left_relation == right_relation:
        return mark_safe('<div class="label label-default">{}</div>'.format(left_relation))
    else:
        deletion = '<div class="label label-danger">-{}</div>'.format(left_relation)
        addition = '<div class="label label-success">+{}</div>'.format(right_relation)
        return mark_safe(deletion + addition)
