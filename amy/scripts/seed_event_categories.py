import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from workshops.models import EventCategory
from workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

DEPRECATED_EVENT_CATEGORIES: list[str] = []

EventCategoryDef = TypedDict(
    "EventCategoryDef",
    {
        "active": bool,
        "id": UUID,
        "name": str,
        "description": str,
    },
)

EVENT_CATEGORIES: list[EventCategoryDef] = [
    {
        "active": True,
        "id": UUID("0c23939f-de98-44c9-969e-29405841676c"),
        "name": "workshop",
        "description": "Workshop",
    },
    {
        "active": True,
        "id": UUID("954ab920-f1d1-4b57-a52c-4d95ab8719d9"),
        "name": "skillup",
        "description": "Skillup",
    },
    {
        "active": True,
        "id": UUID("2de12baf-aa58-45a8-9a8d-fdac593b6708"),
        "name": "training",
        "description": "Training",
    },
    {
        "active": True,
        "id": UUID("42bb1b4b-6698-4d98-8133-8eb87a10314a"),
        "name": "community_session",
        "description": "Community Session",
    },
]

# --------------------------------------------------------------------------------------


def event_category_transform(
    event_category_def: dict[str, Any],
) -> EventCategory:
    return EventCategory(**event_category_def)


def run() -> None:
    seed_models(
        EventCategory,
        cast(list[dict[str, Any]], EVENT_CATEGORIES),
        "name",
        event_category_transform,
        logger,
    )

    deprecate_models(EventCategory, DEPRECATED_EVENT_CATEGORIES, "name", logger)
