from django import template
from django_recaptcha.widgets import ReCaptchaBase

register = template.Library()


@register.filter
def is_captcha(field):
    return isinstance(field.field.widget, ReCaptchaBase)
