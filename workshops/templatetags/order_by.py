from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter_function
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)
