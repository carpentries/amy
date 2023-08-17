from typing import cast

from django import template
from django.contrib.messages.storage.base import Message
from django.http import HttpRequest

from workshops.models import Person

register = template.Library()


@register.simple_tag
def message_allowed(message: Message, request: HttpRequest) -> bool:
    return (
        "only-for-admins" in message.tags
        and request.user
        and cast(Person, request.user).is_admin
        or "only-for-admins" not in message.tags
    )
