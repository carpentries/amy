import logging
from typing import TypedDict

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
        "short_name": str,
        "url_required": bool,
        "date_required": bool,
    },
)

INVOLVEMENTS: list[InvolvementDef] = [
    {
        "display_name": "Served as an Instructor or a helper at a Carpentries workshop",
        "short_name": "Workshop Instructor/Helper",
        "url_required": True,
        "date_required": True,
    },
    {
        "display_name": "Attended an Instructor Meeting, regional meetup, or other community meeting",  # noqa
        "short_name": "Community Meeting",
        "url_required": False,
        "date_required": True,
    },
    {
        "display_name": "Submitted a contribution to a Carpentries repository",
        "short_name": "GitHub Contribution",
        "url_required": True,
        "date_required": True,
    },
    {
        "display_name": "Other:",
        "short_name": "Other",
        "url_required": False,
        "date_required": True,
    },
]

# --------------------------------------------------------------------------------------


def involvement_transform(
    involvement_def: dict,
) -> Involvement:
    return Involvement(**involvement_def)


def run() -> None:
    seed_models(
        Involvement,
        INVOLVEMENTS,
        "short_name",
        involvement_transform,
        logger,
    )

    deprecate_models(Involvement, DEPRECATED_INVOLVEMENTS, "short_name", logger)
