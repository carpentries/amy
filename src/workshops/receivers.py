import logging
from typing import Any

from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.http.request import HttpRequest

# AMY server logger
logger = logging.getLogger("amy")


# a receiver for "failed login attempt" signal
@receiver(user_login_failed)
def log_user_login_failed(sender: Any, **kwargs: Any) -> None:
    request = kwargs.get("request") or HttpRequest()

    ip = request.META.get("REMOTE_ADDR") or "UNKNOWN"
    msg = f"Login failure from IP {ip}"
    logger.error(msg)
