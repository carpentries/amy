from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_or_default_url(next_url: str | None, default: str) -> str:
    if next_url is not None and url_has_allowed_host_and_scheme(next_url, settings.ALLOWED_HOSTS):
        return next_url
    return default


def safe_url(url: str) -> bool:
    return url_has_allowed_host_and_scheme(url, settings.ALLOWED_HOSTS)
