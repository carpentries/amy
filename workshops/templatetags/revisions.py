from django import template

from reversion.revisions import get_for_object

register = template.Library()


@register.inclusion_tag('workshops/last_modified.html')
def last_modified(obj):
    """Get all versions for specific object, display:

    "Created on ASD by DSA."
    "Last modified on ASD by DSA."
    """
    versions = get_for_object(obj)

    try:
        last, *_, created = versions
    except ValueError:  # either len(versions) == 0 or len(versions) == 1
        try:
            created = versions[0]
            last = None
        except IndexError:  # len(versions) == 0
            created = None
            last = None

    return {
        'created': created,
        'last_modified': last,
    }
