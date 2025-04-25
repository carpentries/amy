import logging
from typing import Any, TypedDict, cast

from trainings.models import Involvement
from workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_INVOLVEMENTS: list[str] = []

InvolvementDef = TypedDict(
    "InvolvementDef",
    {
        "display_name": str,
        "name": str,
        "url_required": bool,
        "date_required": bool,
        "notes_required": bool,
    },
)

INVOLVEMENTS: list[InvolvementDef] = [
    {
        "display_name": "Served as an Instructor or a helper at a Carpentries workshop",
        "name": "Workshop Instructor/Helper",
        "url_required": True,
        "date_required": True,
        "notes_required": False,
    },
    {
        "display_name": "Attended a regional meetup, skill-up, or other community meeting",  # noqa
        "name": "Community Meeting",
        "url_required": False,
        "date_required": True,
        "notes_required": True,
    },
    {
        "display_name": "Submitted a contribution to a Carpentries repository on GitHub",  # noqa
        "name": "GitHub Contribution",
        "url_required": True,
        "date_required": True,
        "notes_required": False,
    },
    {
        "display_name": "Other",
        "name": "Other",
        "url_required": False,
        "date_required": True,
        "notes_required": True,
    },
]

# --------------------------------------------------------------------------------------


def involvement_transform(
    involvement_def: dict[str, Any],
) -> Involvement:
    return Involvement(**involvement_def)


def run() -> None:
    seed_models(
        Involvement,
        cast(list[dict[str, Any]], INVOLVEMENTS),
        "name",
        involvement_transform,
        logger,
    )

    deprecate_models(Involvement, DEPRECATED_INVOLVEMENTS, "name", logger)
