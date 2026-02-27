import logging
from typing import Any, Literal, TypedDict, cast
from uuid import UUID

from src.offering.models import Benefit
from src.workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")


class BenefitDef(TypedDict):
    active: bool
    id: UUID
    name: str
    description: str
    unit_type: Literal["seat", "event"]
    credits: int


DEPRECATED_BENEFITS: list[str] = []

BENEFITS: list[BenefitDef] = [
    {
        "active": True,
        "id": UUID("641e0a4c-0626-43f8-ae4f-ccf507b87791"),
        "name": "Instructor Training",
        "description": "Instructor Training default benefit",
        "unit_type": "seat",
        "credits": 1,
    },
    {
        "active": True,
        "id": UUID("c1baac28-e3ba-4a0b-8420-f483b89be125"),
        "name": "Instructor Trainer Training",
        "description": "Instructor Trainer Training default benefit",
        "unit_type": "seat",
        "credits": 1,
    },
    {
        "active": True,
        "id": UUID("829320e4-76b7-43c6-9647-d25d7cbbc9ef"),
        "name": "Collaborative Lesson Development Training",
        "description": "Collaborative Lesson Development Training default benefit",
        "unit_type": "seat",
        "credits": 1,
    },
    {
        "active": True,
        "id": UUID("a7b57542-ad84-45c9-b983-ecdfde0c62f2"),
        "name": "Skillup",
        "description": "Skillup default benefit",
        "unit_type": "seat",
        "credits": 1,
    },
]

# --------------------------------------------------------------------------------------


def benefit_transform(
    benefit_def: dict[str, Any],
) -> Benefit:
    return Benefit(**benefit_def)


def run() -> None:
    seed_models(
        Benefit,
        cast(list[dict[str, Any]], BENEFITS),
        "name",
        benefit_transform,
        logger,
    )

    deprecate_models(Benefit, DEPRECATED_BENEFITS, "name", logger)
