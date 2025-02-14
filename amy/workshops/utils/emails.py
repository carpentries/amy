import re

from django.conf import settings

from dashboard.models import Criterium

WORD_SPLIT = re.compile(r"""([\s<>"']+)""")
SIMPLE_EMAIL = re.compile(r"^\S+@\S+\.\S+$")


def find_emails(text):
    """Find emails in the text.  This is based on Django's own
    `django.utils.html.urlize`."""
    # Split into tokens in case someone uses for example
    # 'Name <name@gmail.com>' format.
    emails = []

    for word in WORD_SPLIT.split(text):
        if SIMPLE_EMAIL.match(word):
            local, domain = word.rsplit("@", 1)
            try:
                domain = domain.encode("idna").decode("ascii")
            except UnicodeError:
                continue
            emails.append("{}@{}".format(local, domain))

    return emails


def match_notification_email(obj):
    """Try to match applied object to a set of criteria (defined in
    `settings.py`)."""
    results = []

    # some objects may not have this attribute, in this case we should fall
    # back to default criteria email
    if hasattr(obj, "country") and obj.country:
        results = Criterium.objects.filter(countries__contains=obj.country).values_list("email", flat=True)
    else:
        # use general notification criteria when event has no country
        results = [settings.ADMIN_NOTIFICATION_CRITERIA_DEFAULT]

    # fallback to default address if nothing matches
    return results or [settings.ADMIN_NOTIFICATION_CRITERIA_DEFAULT]
