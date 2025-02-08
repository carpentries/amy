from typing import Optional

from django import template

from communityroles.models import CommunityRole
from workshops.models import Person
from workshops.utils.dates import human_daterange

register = template.Library()


@register.simple_tag
def get_community_role(person: Person, role_name: str) -> Optional[CommunityRole]:
    try:
        return CommunityRole.objects.get(person=person, config__name=role_name)
    except CommunityRole.DoesNotExist:
        return None


@register.simple_tag
def community_role_human_dates(community_role: CommunityRole) -> str:
    result = human_daterange(community_role.start, community_role.end, no_date_right="present")
    return result
