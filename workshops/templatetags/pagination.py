from django import template
register = template.Library()


@register.inclusion_tag('pagination.html', takes_context=True)
def pagination(context, objects):
    previous = context['request'].GET.copy()
    next = context['request'].GET.copy()
    current = context['request'].GET.copy()
    if 'page' in current:
        del current['page']

    if objects.has_previous():
        previous['page'] = objects.previous_page_number()
    if objects.has_next():
        next['page'] = objects.next_page_number()
    return {'objects': objects, 'prev_query': previous, 'next_query': next,
            'current_query': current}
