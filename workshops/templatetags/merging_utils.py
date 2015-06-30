from django import template
register = template.Library()


@register.simple_tag
def warn_if_different(left, right):
    if left != right:
        return 'bg-danger'
    return ''


@register.simple_tag
def success_if_any_content(obj):
    if obj:
        return 'bg-success'
    return ''
