import re

from workshops.exceptions import InternalError
from workshops.models import Person

NUM_TRIES = 100


def create_username(personal: str, family: str, tries: int = NUM_TRIES) -> str:
    """Generate unique username."""
    stem = normalize_name(family or "") + "_" + normalize_name(personal or "")

    username = stem
    try:
        Person.objects.get(username=username)
    except Person.DoesNotExist:
        return username

    for counter in range(2, tries + 1):
        username = "{0}_{1}".format(stem, counter)
        try:
            Person.objects.get(username=username)
        except Person.DoesNotExist:
            return username

    raise InternalError(
        "Cannot find a non-repeating username"
        "(tried {} usernames): {}.".format(tries, username)
    )


def normalize_name(name):
    """Get rid of spaces, funky characters, etc."""
    name = name.strip()
    for accented, flat in [(" ", "-")]:
        name = name.replace(accented, flat)

    # remove all non-alphanumeric, non-hyphen chars
    name = re.sub(r"[^\w\-]", "", name, flags=re.A)

    # We should use lower-cased username, because it directly corresponds to
    # some files Software Carpentry stores about some people - and, as we know,
    # some filesystems are not case-sensitive.
    return name.lower()
