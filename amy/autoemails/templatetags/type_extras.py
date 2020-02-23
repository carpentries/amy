from collections.abc import Iterable

from django import template
from django.db.models import Model

register = template.Library()


@register.filter
def get_type(value):
    # inspired by: https://stackoverflow.com/a/12028864
    return type(value)


@register.filter
def is_model(value):
    return isinstance(value, Model)


@register.filter
def is_iterable(value):
    return isinstance(value, Iterable)


@register.filter
def is_str(value):
    return isinstance(value, str)


@register.filter
def is_bool(value):
    return isinstance(value, bool)
