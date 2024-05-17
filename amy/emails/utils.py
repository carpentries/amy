from datetime import UTC, date, datetime, timedelta
from functools import partial
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


def combine_date_with_current_utc_time(date: date) -> datetime:
    """Return timezone-aware datetime object combining current time in UTC
    with a given date."""
    current_time_utc = datetime.now(UTC).timetz()
    return datetime.combine(date, current_time_utc)


def shift_date_and_apply_current_utc_time(date: date, offset: timedelta) -> datetime:
    """Return timezone-aware datetime object combining current time in UTC
    with a given date shifted by offset (timedelta).
    Time component of the offset is discarded."""
    date_shifted = date + offset
    return combine_date_with_current_utc_time(date_shifted)


one_month_before = partial(
    shift_date_and_apply_current_utc_time, offset=-timedelta(days=30)
)
two_months_after = partial(
    shift_date_and_apply_current_utc_time, offset=timedelta(days=60)
)


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


def messages_missing_template_link(
    request: HttpRequest, scheduled_email: ScheduledEmail
) -> None:
    messages.warning(
        request,
        f'Email action <a href="{ scheduled_email.get_absolute_url }">'
        f"<code>{ scheduled_email.pk }</code></a> update was not performed due"
        " to missing linked template.",
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_scheduled(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
    name = scheduled_email.template.name if scheduled_email.template else signal_name
    messages.info(
        request,
        format_html(
            "New email action was scheduled to run "
            '<relative-time datetime="{}"></relative-time>: '
            '<a href="{}"><code>{}</code></a>.',
            scheduled_email.scheduled_at,
            scheduled_email.get_absolute_url(),
            name,
        ),
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_updated(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
    name = scheduled_email.template.name if scheduled_email.template else signal_name
    messages.info(
        request,
        format_html(
            'Existing <a href="{}">email action ({})</a> was updated.',
            scheduled_email.get_absolute_url(),
            name,
        ),
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_cancelled(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
    name = scheduled_email.template.name if scheduled_email.template else signal_name
    messages.warning(
        request,
        format_html(
            'Existing <a href="{}">email action ({})</a> was cancelled.',
            scheduled_email.get_absolute_url(),
            name,
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


def api_model_url(model: str, pk: int) -> str:
    return f"api:{model}#{pk}"


def scalar_value_url(type_: str, value: str) -> str:
    return f"value:{type_}#{value}"


scalar_value_none = partial(scalar_value_url, "none", "")
