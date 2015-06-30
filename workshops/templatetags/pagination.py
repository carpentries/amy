from django import template
register = template.Library()


@register.inclusion_tag('pagination.html', takes_context=True)
def pagination(context, objects):
    # needed in set_page_query that's only called from 'pagination.html'
    request = context['request']
    return {'objects': objects, 'request': request}


@register.simple_tag(takes_context=True)
def set_page_query(context, page):
    query = context['request'].GET.copy()
    query['page'] = page
    return query.urlencode()
