import logging
from collections.abc import Callable
from typing import Any, TypedDict, cast

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model

from src.communityroles.models import CommunityRoleConfig, CommunityRoleInactivation
from src.workshops.models import Badge
from src.workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_COMMUNITY_ROLE_CONFIGS: list[str] = []
DEPRECATED_COMMUNITY_ROLE_INACTIVATIONS: list[str] = []


class CommunityRoleConfigDef(TypedDict):
    name: str
    display_name: str
    link_to_award: bool
    award_badge_limit__name: str | None
    autoassign_when_award_created: bool
    link_to_membership: bool
    link_to_partnership: bool
    additional_url: bool
    generic_relation_content_type__app_label: str | None
    generic_relation_content_type__model: str | None
    custom_key_labels: list[str]


class CommunityRoleInactivationDef(TypedDict):
    name: str


COMMUNITY_ROLE_CONFIGS: list[CommunityRoleConfigDef] = [
    {
        "name": "maintainer",
        "display_name": "Maintainer",
        "link_to_award": True,
        "award_badge_limit__name": "maintainer",
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": False,
        "generic_relation_content_type__app_label": "workshops",
        "generic_relation_content_type__model": "lesson",
        "custom_key_labels": [],
    },
    {
        "name": "trainer",
        "display_name": "Trainer",
        "link_to_award": True,
        "award_badge_limit__name": "trainer",
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": False,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
    {
        "name": "instructor",
        "display_name": "Instructor",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": False,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
    {
        "name": "curriculum_advisor",
        "display_name": "Curriculum Advisor",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": False,
        "generic_relation_content_type__app_label": "workshops",
        "generic_relation_content_type__model": "curriculum",
        "custom_key_labels": [],
    },
    {
        "name": "committee_member",
        "display_name": "Committee Member",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": False,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
    {
        "name": "task_force_member",
        "display_name": "Task Force Member",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": False,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
    {
        "name": "regional_coordinator",
        "display_name": "Regional Coordinator",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": False,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
    {
        "name": "carpentries_lab_editor",
        "display_name": "The Carpentries Lab Editor",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": True,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
    {
        "name": "carpentries_lab_reviewer",
        "display_name": "The Carpentries Lab Reviewer",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": False,
        "additional_url": True,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
    {
        "name": "partnership_trainer",
        "display_name": "Partnership Trainer",
        "link_to_award": False,
        "award_badge_limit__name": None,
        "autoassign_when_award_created": False,
        "link_to_membership": False,
        "link_to_partnership": True,
        "additional_url": False,
        "generic_relation_content_type__app_label": None,
        "generic_relation_content_type__model": None,
        "custom_key_labels": [],
    },
]
COMMUNITY_ROLE_INACTIVATIONS: list[CommunityRoleInactivationDef] = [
    {
        "name": "Stepped down",
    },
    {
        "name": "Unresponsive",
    },
    {
        "name": "End of term",
    },
    {
        "name": "Suspension",
    },
    {
        "name": "Termination",
    },
]

# --------------------------------------------------------------------------------------


def config_transform(config_def: CommunityRoleConfigDef) -> CommunityRoleConfig:
    badge = None
    if badge_name := config_def["award_badge_limit__name"]:
        badge = Badge.objects.get(name=badge_name)

    content_type = None
    if (ct_app_label := config_def["generic_relation_content_type__app_label"]) and (
        ct_model := config_def["generic_relation_content_type__model"]
    ):
        content_type = ContentType.objects.get(app_label=ct_app_label, model=ct_model)

    return CommunityRoleConfig(
        name=config_def["name"],
        display_name=config_def["display_name"],
        link_to_award=config_def["link_to_award"],
        award_badge_limit=badge,
        autoassign_when_award_created=config_def["autoassign_when_award_created"],
        link_to_membership=config_def["link_to_membership"],
        link_to_partnership=config_def["link_to_partnership"],
        additional_url=config_def["additional_url"],
        generic_relation_content_type=content_type,
        custom_key_labels=config_def["custom_key_labels"],
    )


def inactivation_transform(inactivation_def: dict[str, Any]) -> CommunityRoleInactivation:
    return CommunityRoleInactivation(**inactivation_def)


def run() -> None:
    seed_models(
        CommunityRoleConfig,
        cast(list[dict[str, Any]], COMMUNITY_ROLE_CONFIGS),
        "name",
        cast(Callable[[dict[str, Any]], Model], config_transform),
        logger,
    )
    seed_models(
        CommunityRoleInactivation,
        cast(list[dict[str, Any]], COMMUNITY_ROLE_INACTIVATIONS),
        "name",
        inactivation_transform,
        logger,
    )

    deprecate_models(CommunityRoleConfig, DEPRECATED_COMMUNITY_ROLE_CONFIGS, "name", logger)
    deprecate_models(
        CommunityRoleInactivation,
        DEPRECATED_COMMUNITY_ROLE_INACTIVATIONS,
        "name",
        logger,
    )
