import logging
from typing import TypedDict

from workshops.models import TrainingRequirement
from workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_TRAINING_REQUIREMENTS: list[str] = []

TrainingRequirementDef = TypedDict(
    "TrainingRequirementDef",
    {
        "name": str,
        "url_required": bool,
        "event_required": bool,
    },
)

TRAINING_REQUIREMENTS: list[TrainingRequirementDef] = [
    {"name": "Training", "url_required": False, "event_required": True},
    {"name": "DC Homework", "url_required": True, "event_required": False},
    {"name": "SWC Homework", "url_required": True, "event_required": False},
    {"name": "Welcome Session", "url_required": False, "event_required": False},
    {"name": "DC Demo", "url_required": False, "event_required": False},
    {"name": "SWC Demo", "url_required": False, "event_required": False},
    {"name": "LC Demo", "url_required": False, "event_required": False},
    {"name": "LC Homework", "url_required": True, "event_required": False},
    {"name": "Lesson Contribution", "url_required": True, "event_required": False},
    {"name": "Demo", "url_required": False, "event_required": False},
]

# --------------------------------------------------------------------------------------


def training_requirement_transform(
    training_requirement_def: dict,
) -> TrainingRequirement:
    return TrainingRequirement(**training_requirement_def)


def run() -> None:
    seed_models(
        TrainingRequirement,
        TRAINING_REQUIREMENTS,
        "name",
        training_requirement_transform,
        logger,
    )

    deprecate_models(
        TrainingRequirement, DEPRECATED_TRAINING_REQUIREMENTS, "name", logger
    )
