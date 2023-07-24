import logging
from typing import TypedDict
from uuid import UUID

from emails.models import EmailTemplate
from emails.signals import SignalName
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
        id=UUID("05e2b9da-e6b3-43f0-8c88-1458414b8945"),
        name="Instructor Badge awarded",
        signal=SignalName.instructor_badge_awarded,
        from_header="instructor.training@carpentries.org",
        reply_to_header="",
        cc_header=["instructor.training@carpentries.org"],
        bcc_header=[],
        subject="Congratulations! You are a certified Carpentries Instructor",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "Congratulations, you are a badged Instructor. "
            "Your certificate is attached to this email. Here's how to get involved."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("e07e889b-cc5e-4eb1-9cf6-5f416da9ddaf"),
        name="Instructor confirmed for workshop",
        signal=SignalName.instructor_confirmed_for_workshop,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=["workshops@carpentries.org"],
        bcc_header=[],
        subject="You are confirmed to teach (workshop)",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "We have confirmed you to teach at (TODO event). For more details go to..."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("ce73a58e-eb31-41bd-af95-f5bdbc4db5d4"),
        name="Instructor declined from workshop",
        signal=SignalName.instructor_declined_from_workshop,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=["workshops@carpentries.org"],
        bcc_header=[],
        subject="(Workshop): Other Instructors placed",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "Thank you for your interest in (TODO event). We have confirmed "
            "other instructors for this workshop. Please continue to join..."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("6931cf24-2e94-4f70-825e-e41b431f1d24"),
        name="Instructor Signs Up for Workshop",
        signal=SignalName.instructor_signs_up_for_workshop,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=["workshops@carpentries.org"],
        bcc_header=[],
        subject="Thank you for expressing interest in teaching (workshop)",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "Thank you for your interest in teaching (TODO: workshop summary). "
            "Our team will get back to you shortly."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("2de9852e-d2e9-4b10-bcfb-0b19f21e2094"),
        name="Admin Signs Instructor Up for Workshop",
        signal=SignalName.admin_signs_instructor_up_for_workshop,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=["workshops@carpentries.org"],
        bcc_header=[],
        subject="Thank you for expressing interest in teaching (workshop)",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "At your request, we have registered your interest in teaching "
            "(TODO: workshop summary). You may log in to your AMY profile at any time "
            "to view or make updates. Our team will get back to you shortly."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("5703079f-2f37-4aee-8267-fe6db3eee870"),
        name="Person records are merged",
        signal=SignalName.persons_merged,
        from_header="team@carpentries.org",
        reply_to_header="",
        cc_header=["team@carpentries.org"],
        bcc_header=[],
        subject="The Carpentries Database: Multiple records",
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
