from typing import cast

from django import template
from django.conf import settings
from django.contrib.messages.storage.base import Message
from django.http import HttpRequest

from workshops.models import Person

register = template.Library()


@register.simple_tag
def message_allowed(message: Message, request: HttpRequest) -> bool:
    return (
        settings.ONLY_FOR_ADMINS_TAG in message.tags
        and request.user
        and cast(Person, request.user).is_admin
        or settings.ONLY_FOR_ADMINS_TAG not in message.tags
    )
