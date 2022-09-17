from hashlib import sha1

from django.conf import settings


def reports_link_hash(slug: str) -> str:
    """Generate hash for accessing workshop reports repository."""
    lowered = slug.lower()
    salt_front = settings.REPORTS_SALT_FRONT
    salt_back = settings.REPORTS_SALT_BACK
    hashed = sha1(f"{salt_front}{lowered}{salt_back}".encode("utf-8"))
    return hashed.hexdigest()


def reports_link(slug: str) -> str:
    """Return link to workshop's reports with hash and slug filled in."""
    hashed = reports_link_hash(slug)
    link = settings.REPORTS_LINK
    return link.format(hash=hashed, slug=slug)
