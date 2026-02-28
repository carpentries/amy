import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from src.offering.models import AccountBenefitDiscount
from src.workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")


class AccountBenefitDiscountDef(TypedDict):
    id: UUID
    name: str


DEPRECATED_ACCOUNT_BENEFIT_DISCOUNTS: list[str] = []

ACCOUNT_BENEFIT_DISCOUNTS: list[AccountBenefitDiscountDef] = [
    {
        "id": UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        "name": "Partial Sponsorship",
    },
    {
        "id": UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901"),
        "name": "Full Discount",
    },
    {
        "id": UUID("c3d4e5f6-a7b8-9012-cdef-123456789012"),
        "name": "Trainer Discount",
    },
]

# --------------------------------------------------------------------------------------


def account_benefit_discount_transform(
    discount_def: dict[str, Any],
) -> AccountBenefitDiscount:
    return AccountBenefitDiscount(**discount_def)


def run() -> None:
    seed_models(
        AccountBenefitDiscount,
        cast(list[dict[str, Any]], ACCOUNT_BENEFIT_DISCOUNTS),
        "name",
        account_benefit_discount_transform,
        logger,
    )

    deprecate_models(
        AccountBenefitDiscount,
        DEPRECATED_ACCOUNT_BENEFIT_DISCOUNTS,
        "name",
        logger,
    )
