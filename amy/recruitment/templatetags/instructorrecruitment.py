from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def is_instructor_recruitment_enabled():
    try:
        return bool(settings.INSTRUCTOR_RECRUITMENT_ENABLED)
    except AttributeError:
        return False
