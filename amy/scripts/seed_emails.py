import logging
from typing import TypedDict
from uuid import UUID

from emails.models import EmailTemplate
from workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_EMAIL_TEMPLATES: list[str] = []

EmailTemplateDef = TypedDict(
    "EmailTemplateDef",
    {
        "active": bool,
        "id": UUID,
        "name": str,
        "signal": str,
        "from_header": str,
        "reply_to_header": str,
        "cc_header": list[str],
        "bcc_header": list[str],
        "subject": str,
        "body": str,
    },
)

EMAIL_TEMPLATES: list[EmailTemplateDef] = [
    EmailTemplateDef(
        active=True,
        id=UUID("5703079f-2f37-4aee-8267-fe6db3eee870"),
        name="Person records are merged",
        signal="persons_merged",
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="The Carpentries: merged duplicate profiles",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "We saw that you had two profiles in our database. "
            "We have merged them. "
            "Log in to AMY to view your profile and verify things are correct."
        ),
    ),
]


def email_template_transform(email_template_def: dict) -> EmailTemplate:
    return EmailTemplate(**email_template_def)


def run() -> None:
    seed_models(
        EmailTemplate, EMAIL_TEMPLATES, "signal", email_template_transform, logger
    )

    deprecate_models(EmailTemplate, DEPRECATED_EMAIL_TEMPLATES, "id", logger)
