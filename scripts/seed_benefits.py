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
