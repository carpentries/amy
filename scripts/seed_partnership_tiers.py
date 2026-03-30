import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from src.fiscal.models import PartnershipTier
from src.workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")


class PartnershipTierDef(TypedDict):
    id: UUID
    name: str
    credits: int
    is_custom: bool


DEPRECATED_PARTNERSHIP_TIERS: list[str] = []

PARTNERSHIP_TIERS: list[PartnershipTierDef] = [
    {
        "id": UUID("d4e5f6a7-b8c9-0123-defa-234567890123"),
        "name": "Custom",
        "credits": 0,
        "is_custom": True,
    },
]

# --------------------------------------------------------------------------------------


def partnership_tier_transform(tier_def: dict[str, Any]) -> PartnershipTier:
    return PartnershipTier(**tier_def)


def run() -> None:
    seed_models(
        PartnershipTier,
        cast(list[dict[str, Any]], PARTNERSHIP_TIERS),
        "name",
        partnership_tier_transform,
        logger,
    )

    deprecate_models(
        PartnershipTier,
        DEPRECATED_PARTNERSHIP_TIERS,
        "name",
        logger,
    )
