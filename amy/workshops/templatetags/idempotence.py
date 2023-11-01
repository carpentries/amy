from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def idempotence_token(context):
    token = context["idempotence_token"]
    html = format_html(
        '<input type="hidden" name="idempotence_token" value="{token}">', token=token
    )
    return html
