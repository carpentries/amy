from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def idempotence_token(context):
    token = context.get("idempotence_token")
    if token:
        html = format_html(
            '<input type="hidden" name="idempotence_token" value="{token}">',
            token=token,
        )
    else:
        html = ""
    return html
