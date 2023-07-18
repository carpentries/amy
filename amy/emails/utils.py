from datetime import datetime, timedelta
import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html

from emails.models import ScheduledEmail

logger = logging.getLogger("amy")


def check_feature_flag() -> bool:
    """Receivers will be connected no matter if EMAIL_MODULE_ENABLED is set or not.
    This function helps check if the receiver should exit early when the feature flag
    is disabled."""
    return settings.EMAIL_MODULE_ENABLED is True


def feature_flag_enabled(func):
    """Check if the feature flag is enabled before running the receiver.
    If the feature flag is disabled, the receiver will exit early and not run."""

    def wrapper(*args, **kwargs):
        if not check_feature_flag():
            logger.debug(
                f"EMAIL_MODULE_ENABLED not set, skipping receiver {func.__name__}"
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
        f"Action was not scheduled due to missing template for signal {signal}.",
    )


def messages_action_scheduled(
    request: HttpRequest, scheduled_email: ScheduledEmail
) -> None:
    messages.info(
        request,
        format_html(
            'Action was scheduled: <a href="{}">{}</a>.',
            scheduled_email.get_absolute_url(),
            scheduled_email.pk,
        ),
    )
