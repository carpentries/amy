from django import template

from reversion.models import Version

register = template.Library()


@register.inclusion_tag('workshops/last_modified.html')
def last_modified(obj):
    """Get all versions for specific object, display:

    "Created on ASD by DSA."
    "Last modified on ASD by DSA."
    """
    versions = Version.objects.get_for_object(obj)

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
