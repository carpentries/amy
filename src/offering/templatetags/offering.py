from django import template
from django.contrib.auth.models import AnonymousUser

from src.offering.utils import is_account_owner
from src.workshops.models import Person

register = template.Library()


@register.simple_tag(name="is_account_owner")
def is_account_owner_tag(person: Person | AnonymousUser) -> bool:
    return is_account_owner(person)
