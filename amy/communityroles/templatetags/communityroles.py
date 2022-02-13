from typing import Optional

from django import template

from communityroles.models import CommunityRole
from workshops.models import Person

register = template.Library()


@register.simple_tag
def get_community_role(person: Person, role_name: str) -> Optional[CommunityRole]:
    try:
        return CommunityRole.objects.get(person=person, config__name=role_name)
    except CommunityRole.DoesNotExist:
        return None
