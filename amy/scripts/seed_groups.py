from logging import Logger, getLogger
from typing import Sequence, TypedDict

from django.contrib.auth.models import Group, Permission

from workshops.utils.seeding import deprecate_models

logger = getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_GROUPS: list[str] = []  # todo: include current AMY groups

GroupDef = TypedDict(
    "GroupDef",
    {"name": str, "permissions": list[str]},
)

GROUPS: list[GroupDef] = [
    {
        "name": "view_all",
        "permissions": [
            "view_airport",
            "view_person",
            "view_tag",
            "view_event",
            "view_role",
            "view_task",
            "view_qualification",
            "view_badge",
            "view_award",
            "view_logentry",
            "view_lesson",
            "view_knowledgedomain",
            "view_revision",
            "view_version",
            "view_academiclevel",
            "view_computingexperiencelevel",
            "view_membership",
            "view_language",
            "view_trainingrequest",
            "view_organization",
            "view_trainingrequirement",
            "view_trainingprogress",
            "view_association",
            "view_code",
            "view_nonce",
            "view_partial",
            "view_usersocialauth",
            "view_curriculum",
            "view_workshoprequest",
            "view_site",
            "view_commentflag",
            "view_comment",
            "view_criterium",
            "view_continent",
            "view_infosource",
            "view_datavariant",
            "view_workshopinquiryrequest",
            "view_selforganisedsubmission",
            "view_emailtemplate",
            "view_trigger",
            "view_rqjob",
            "view_memberrole",
            "view_member",
            "view_membershippersonrole",
            "view_membershiptask",
            "view_term",
            "view_termoption",
            "view_consent",
            "view_communityroleinactivation",
            "view_communityroleconfig",
            "view_communityrole",
            "view_instructorrecruitment",
            "view_instructorrecruitmentsignup",
        ],
    },
    {
        "name": "membership_administrators",
        "permissions": [
            "add_person",
            "view_person",
            "add_membership",
            "change_membership",
            "delete_membership",
            "view_membership",
            "add_organization",
            "view_organization",
            "add_comment",
            "change_comment",
            "delete_comment",
            "view_comment",
            "add_member",
            "change_member",
            "delete_member",
            "view_member",
            "add_membershiptask",
            "change_membershiptask",
            "delete_membershiptask",
            "view_membershiptask",
        ],
    },
    {
        "name": "workshop_administrators",
        "permissions": [
            "add_person",
            "view_person",
            "add_event",
            "change_event",
            "delete_event",
            "view_event",
            "add_task",
            "change_task",
            "delete_task",
            "view_task",
            "add_organization",
            "view_organization",
            "add_workshoprequest",
            "change_workshoprequest",
            "delete_workshoprequest",
            "view_workshoprequest",
            "add_comment",
            "change_comment",
            "delete_comment",
            "view_comment",
            "add_workshopinquiryrequest",
            "change_workshopinquiryrequest",
            "delete_workshopinquiryrequest",
            "view_workshopinquiryrequest",
            "add_selforganisedsubmission",
            "change_selforganisedsubmission",
            "delete_selforganisedsubmission",
            "view_selforganisedsubmission",
            "add_instructorrecruitment",
            "change_instructorrecruitment",
            "delete_instructorrecruitment",
            "view_instructorrecruitment",
            "add_instructorrecruitmentsignup",
            "change_instructorrecruitmentsignup",
            "delete_instructorrecruitmentsignup",
            "view_instructorrecruitmentsignup",
        ],
    },
    {
        "name": "instructor_training_administrators",
        "permissions": [
            "add_person",
            "change_person",
            "view_person",
            "add_task",
            "change_task",
            "delete_task",
            "view_task",
            "add_award",
            "change_award",
            "delete_award",
            "view_award",
            "view_membership",
            "add_trainingrequest",
            "change_trainingrequest",
            "delete_trainingrequest",
            "view_trainingrequest",
            "add_organization",
            "view_organization",
            "add_trainingprogress",
            "change_trainingprogress",
            "delete_trainingprogress",
            "view_trainingprogress",
            "add_comment",
            "change_comment",
            "delete_comment",
            "view_comment",
            "add_communityrole",
            "change_communityrole",
            "delete_communityrole",
            "view_communityrole",
        ],
    },
    {
        "name": "curriculum_administrators",
        "permissions": [
            "view_person",
            "add_award",
            "change_award",
            "delete_award",
            "view_award",
            "add_organization",
            "view_organization",
            "add_communityrole",
            "change_communityrole",
            "delete_communityrole",
            "view_communityrole",
        ],
    },
    {
        "name": "amy_administrators",
        "permissions": [
            "add_tag",
            "change_tag",
            "delete_tag",
            "view_tag",
            "add_role",
            "change_role",
            "delete_role",
            "view_role",
            "add_badge",
            "change_badge",
            "delete_badge",
            "view_badge",
            "view_logentry",
            "add_lesson",
            "change_lesson",
            "delete_lesson",
            "view_lesson",
            "add_knowledgedomain",
            "change_knowledgedomain",
            "delete_knowledgedomain",
            "view_knowledgedomain",
            "add_academiclevel",
            "change_academiclevel",
            "delete_academiclevel",
            "view_academiclevel",
            "add_computingexperiencelevel",
            "change_computingexperiencelevel",
            "delete_computingexperiencelevel",
            "view_computingexperiencelevel",
            "add_language",
            "change_language",
            "delete_language",
            "view_language",
            "add_trainingrequirement",
            "change_trainingrequirement",
            "delete_trainingrequirement",
            "view_trainingrequirement",
            "add_usersocialauth",
            "change_usersocialauth",
            "delete_usersocialauth",
            "add_curriculum",
            "change_curriculum",
            "delete_curriculum",
            "view_curriculum",
            "add_site",
            "change_site",
            "delete_site",
            "view_site",
            "add_criterium",
            "change_criterium",
            "delete_criterium",
            "view_criterium",
            "add_continent",
            "change_continent",
            "delete_continent",
            "view_continent",
            "add_infosource",
            "change_infosource",
            "delete_infosource",
            "view_infosource",
            "add_datavariant",
            "change_datavariant",
            "delete_datavariant",
            "view_datavariant",
            "add_emailtemplate",
            "change_emailtemplate",
            "delete_emailtemplate",
            "view_emailtemplate",
            "add_trigger",
            "change_trigger",
            "delete_trigger",
            "view_trigger",
            "add_rqjob",
            "change_rqjob",
            "delete_rqjob",
            "view_rqjob",
            "add_memberrole",
            "change_memberrole",
            "delete_memberrole",
            "view_memberrole",
            "add_membershippersonrole",
            "change_membershippersonrole",
            "delete_membershippersonrole",
            "view_membershippersonrole",
            "add_term",
            "change_term",
            "delete_term",
            "view_term",
            "add_termoption",
            "change_termoption",
            "delete_termoption",
            "view_termoption",
            "add_communityroleinactivation",
            "change_communityroleinactivation",
            "delete_communityroleinactivation",
            "view_communityroleinactivation",
            "add_communityroleconfig",
            "change_communityroleconfig",
            "delete_communityroleconfig",
            "view_communityroleconfig",
        ],
    },
    {
        "name": "misc",
        "permissions": [
            "add_airport",
            "change_airport",
            "delete_airport",
            "view_airport",
            "view_revision",
            "view_version",
        ],
    },
    {
        "name": "regional_coordinators",
        "permissions": [],
    },
    {
        "name": "executive_council",
        "permissions": [],
    },
    # regular instructors are handled implicitly
    # by the login_required tag/LoginRequiredMixin mixin.
    # superusers are set some other way - todo
]

# --------------------------------------------------------------------------------------


def group_transform(group_def: dict) -> Group:
    permissions = Permission.objects.filter(codename__in=group_def["permissions"])

    return Group(name=group_def["name"], permissions=permissions)


def seed_groups(
    group_definition_list: Sequence[TypedDict],
    logger: Logger | None = None,
) -> None:
    """
    Custom seeding function because can't set M2M fields (like permissions) during
    object creation
    """

    def _info(msg: str) -> None:
        if logger:
            logger.info(msg)

    model_class = Group
    class_name = model_class.__name__

    _info(f"Start of {class_name} seeding.")

    for i, group_definition in enumerate(group_definition_list):
        group_name = group_definition["name"]

        if Group.objects.filter(name=group_name).exists():
            _info(f"{i} {class_name} <{group_name}> already exists, skipping.")
            continue

        _info(f"{i} {class_name} <{group_name}> doesn't exist, creating.")

        group = Group(name=group_name)
        group.save()

        _info(f"{i} {class_name} <{group_name}> setting permissions.")
        permissions = Permission.objects.filter(
            codename__in=group_definition["permissions"]
        )
        group.permissions.set(permissions)

    _info(f"End of {class_name} seeding.")


def run() -> None:
    seed_groups(GROUPS, logger)

    deprecate_models(Group, DEPRECATED_GROUPS, "name", logger)
