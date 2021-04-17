import logging

from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.http.request import HttpRequest

# AMY server logger
logger = logging.getLogger("amy.server_logs")


# a receiver for "failed login attempt" signal
@receiver(user_login_failed)
def log_user_login_failed(sender, **kwargs):
    credentials = kwargs.get("credentials") or dict()
    request = kwargs.get("request") or HttpRequest()

    ip = request.META.get("REMOTE_ADDR") or "UNKNOWN"
    username = credentials.get("username") or "UNKNOWN"
    msg = "Login failure from IP {} for user '{}'".format(ip, username)
    logger.error(msg)
