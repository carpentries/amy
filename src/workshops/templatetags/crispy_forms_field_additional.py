from django import template
from django.forms.boundfield import BoundField
from django_recaptcha.widgets import ReCaptchaBase

register = template.Library()


@register.filter
def is_captcha(field: BoundField) -> bool:
    return isinstance(field.field.widget, ReCaptchaBase)
