import logging
from typing import Any, TypedDict, cast

from src.workshops.models import Badge
from src.workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_BADGES: list[str] = []


class BadgeDef(TypedDict):
    name: str
    title: str
    criteria: str


BADGES: list[BadgeDef] = [
    {
        "name": "swc-instructor",
        "title": "Software Carpentry Instructor",
        "criteria": "Teaching at Software Carpentry workshops or online",
    },
    {
        "name": "dc-instructor",
        "title": "Data Carpentry Instructor",
        "criteria": "Teaching at Data Carpentry workshops or online",
    },
    {
        "name": "maintainer",
        "title": "Maintainer",
        "criteria": "Maintainer of Software or Data Carpentry lesson",
    },
    {
        "name": "trainer",
        "title": "Trainer",
        "criteria": "Teaching instructor training workshops",
    },
    {
        "name": "mentor",
        "title": "Mentor",
        "criteria": "Mentor of Carpentry Instructors",
    },
    {
        "name": "mentee",
        "title": "Mentee",
        "criteria": "Mentee in Carpentry Mentorship Program",
    },
    {
        "name": "lc-instructor",
        "title": "Library Carpentry Instructor",
        "criteria": "Teaching at Library Carpentry workshops or online",
    },
    {
        "name": "creator",
        "title": "Creator",
        "criteria": "Creating learning materials and other content",
    },
    {
        "name": "member",
        "title": "Member",
        "criteria": "Software Carpentry Foundation member",
    },
    {
        "name": "organizer",
        "title": "Organizer",
        "criteria": "Organizing workshops and learning groups",
    },
    {
        "name": "instructor",
        "title": "Instructor",
        "criteria": "Teaching at The Carpentries workshops or online",
    },
]

# --------------------------------------------------------------------------------------


def badge_transform(badge_def: dict[str, Any]) -> Badge:
    return Badge(**badge_def)


def run() -> None:
    seed_models(Badge, cast(list[dict[str, Any]], BADGES), "name", badge_transform, logger)

    deprecate_models(Badge, DEPRECATED_BADGES, "name", logger)
