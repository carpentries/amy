from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def is_email_module_enabled() -> bool:
    try:
        return bool(settings.EMAIL_MODULE_ENABLED)
    except AttributeError:
        return False
