import logging
from typing import Any, TypedDict, cast

from workshops.models import TrainingRequirement
from workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_TRAINING_REQUIREMENTS: list[str] = [
    "DC Homework",
    "SWC Homework",
    "LC Homework",
    "DC Demo",
    "SWC Demo",
    "LC Demo",
]

TrainingRequirementDef = TypedDict(
    "TrainingRequirementDef",
    {
        "name": str,
        "url_required": bool,
        "event_required": bool,
        "involvement_required": bool,
    },
)

TRAINING_REQUIREMENTS: list[TrainingRequirementDef] = [
    {
        "name": "Training",
        "url_required": False,
        "event_required": True,
        "involvement_required": False,
    },
    {
        "name": "Welcome Session",
        "url_required": False,
        "event_required": False,
        "involvement_required": False,
    },
    {
        "name": "Get Involved",
        "url_required": False,
        "event_required": False,
        "involvement_required": True,
    },
    {
        "name": "Demo",
        "url_required": False,
        "event_required": False,
        "involvement_required": False,
    },
]

# --------------------------------------------------------------------------------------


def training_requirement_transform(
    training_requirement_def: dict[str, Any],
) -> TrainingRequirement:
    return TrainingRequirement(**training_requirement_def)


def run() -> None:
    seed_models(
        TrainingRequirement,
        cast(list[dict[str, Any]], TRAINING_REQUIREMENTS),
        "name",
        training_requirement_transform,
        logger,
    )

    deprecate_models(TrainingRequirement, DEPRECATED_TRAINING_REQUIREMENTS, "name", logger)
