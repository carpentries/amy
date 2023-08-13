from datetime import datetime, timedelta
import logging
from typing import Iterable, cast

from django.contrib import messages
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from flags import conditions
from flags.state import flag_enabled

from emails.models import ScheduledEmail
from emails.signals import Signal
from workshops.models import Person

logger = logging.getLogger("amy")


@conditions.register("session")  # type: ignore
def session_condition(value, request: HttpRequest, **kwargs):
    """Additional condition for django-flags. It reads a specific value from
    request session."""
    return request.session.get(value, False)


def feature_flag_enabled(func):
    """Check if the feature flag is enabled before running the receiver.
    If the feature flag is disabled, the receiver will exit early and not run."""

    def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not (request and flag_enabled("EMAIL_MODULE", request=request)):
            logger.debug(
                f"EMAIL_MODULE feature flag not set, skipping receiver {func.__name__}"
            )
            return
        return func(*args, **kwargs)

    return wrapper


def immediate_action() -> datetime:
    """Timezone-aware datetime object for immediate action (supposed to run after
    1 hour from being scheduled)."""
    return timezone.now() + timedelta(hours=1)


def messages_missing_template(request: HttpRequest, signal: str) -> None:
    messages.warning(
        request,
        f"Email action was not scheduled due to missing template for signal {signal}.",
    )


def messages_action_scheduled(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
    messages.info(
        request,
        format_html(
            "New email action ({}) was scheduled to run "
            '<relative-time datetime="{}"></relative-time>: '
            '<a href="{}"><code>{}</code></a>.',
            signal_name,
            scheduled_email.scheduled_at,
            scheduled_email.get_absolute_url(),
            scheduled_email.pk,
        ),
    )


def person_from_request(request: HttpRequest) -> Person | None:
    """Simplify getting person from request, or None if they're not authenticated."""
    if (
        not hasattr(request, "user")  # field often not present in unit tests
        or not request.user.is_authenticated  # don't return AnonymousUser
    ):
        return None

    return cast(Person, request.user)


def find_signal_by_name(
    signal_name: str, all_signals: Iterable[Signal]
) -> Signal | None:
    return next(
        (signal for signal in all_signals if signal.signal_name == signal_name),
        None,
    )
