from datetime import date, datetime, timedelta
import logging
from typing import Iterable, cast

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from flags import conditions

from emails.models import ScheduledEmail
from emails.signals import Signal
from workshops.models import Person

logger = logging.getLogger("amy")


@conditions.register("session")  # type: ignore
def session_condition(value, request: HttpRequest, **kwargs):
    """Additional condition for django-flags. It reads a specific value from
    request session."""
    return request.session.get(value, False)


def immediate_action() -> datetime:
    """Timezone-aware datetime object for immediate action (supposed to run after
    1 hour from being scheduled)."""
    return timezone.now() + timedelta(hours=1)


def one_month_before(date: date) -> datetime:
    """Timezone-aware datetime object for action scheduled one month before, uses
    current time in UTC as time component of the returned datetime object."""
    current_time_utc = datetime.now(timezone.utc).time()
    date_shifted = date - timedelta(days=30)
    return datetime.combine(date_shifted, current_time_utc)  # TODO: fix naive datetime


def messages_missing_recipients(request: HttpRequest, signal: str) -> None:
    messages.warning(
        request,
        f"Email action was not scheduled due to missing recipients for signal {signal}."
        " Please check if the persons involved have email addresses set.",
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_missing_template(request: HttpRequest, signal: str) -> None:
    messages.warning(
        request,
        f"Email action was not scheduled due to missing template for signal {signal}.",
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
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
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_cancelled(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
    messages.info(
        request,
        format_html(
            'Existing <a href="{}">email action ({})</a> was cancelled.',
            scheduled_email.get_absolute_url(),
            signal_name,
        ),
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
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
