import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from src.emails.models import EmailTemplate
from src.emails.signals import SignalNameEnum
from src.workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_EMAIL_TEMPLATES: list[str] = []


class EmailTemplateDef(TypedDict):
    active: bool
    id: UUID
    name: str
    signal: str
    from_header: str
    reply_to_header: str
    cc_header: list[str]
    bcc_header: list[str]
    subject: str
    body: str


EMAIL_TEMPLATES: list[EmailTemplateDef] = [
    EmailTemplateDef(
        active=True,
        id=UUID("05e2b9da-e6b3-43f0-8c88-1458414b8945"),
        name="Instructor Badge awarded",
        signal=SignalNameEnum.instructor_badge_awarded,
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
        signal=SignalNameEnum.instructor_confirmed_for_workshop,
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
        signal=SignalNameEnum.instructor_declined_from_workshop,
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
        signal=SignalNameEnum.instructor_signs_up_for_workshop,
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
        signal=SignalNameEnum.admin_signs_instructor_up_for_workshop,
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
        signal=SignalNameEnum.persons_merged,
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
    EmailTemplateDef(
        active=True,
        id=UUID("8419c339-6997-47ce-b272-bfa98b447364"),
        name="Instructor task created for workshop",
        signal=SignalNameEnum.instructor_task_created_for_workshop,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="You will teach (workshop)",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "We have added you to teach at (TODO event). For more details go to..."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("a002c623-b849-4843-a589-08020f4b8589"),
        name="Instructor Training Approaching",
        signal=SignalNameEnum.instructor_training_approaching,
        from_header="instructor.training@carpentries.org",
        reply_to_header="",
        cc_header=["instructor.training@carpentries.org"],
        bcc_header=[],
        subject="(Workshop) is one month away!",
        body=(
            "Hi, {{ instructor.0.personal }} {{ instructor.0.family }} and "
            "{{ instructor.1.personal }} {{ instructor.1.family }}."
            "Thank you for participating in the instructor training program. "
            "Your training is one month away. Please be sure to do the following... "
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("17234a5e-a15e-4314-a328-783f917d6630"),
        name="Instructor Training completed but not yet badged",
        signal=SignalNameEnum.instructor_training_completed_not_badged,
        from_header="instructor.training@carpentries.org",
        reply_to_header="",
        cc_header=["instructor.training@carpentries.org"],
        bcc_header=[],
        subject="Carpentries Instructor Training Deadline Approaching",
        body=(
            "Hi, {{ person.personal }} {{ person.family }}. "
            "Thank you for joining the Carpentries instructor training on (date). "
            "You have completed the following steps towards certification "
            "(passed requirements). "
            "Here's what you have left to do: (missing requirements)."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("4e737df8-d2ef-4ebd-9a26-087212af233b"),
        name="New / renewing membership starting (member onboarding)",
        signal=SignalNameEnum.new_membership_onboarding,
        from_header="membership@carpentries.org",
        reply_to_header="",
        cc_header=["membership@carpentries.org"],
        bcc_header=[],
        subject="Carpentries Membership with (member names), (member start-end dates)",
        body=(
            "Thank you for joining The Carpentries as a member organization. "
            "Here is information to get you started: "
            "https://carpentries.org/membership/"
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("e368058b-7e3b-4717-b9e9-0b8765bd0d0d"),
        name="Host-instructors introduction",
        signal=SignalNameEnum.host_instructors_introduction,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Instructors for workshop at {{ event.venue }} on {{ event.start }}",
        body="Hey {{ host }}, this is {{ instructors.0 }} and {{ instructors.1 }} for event {{ event }}.",
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("b5a3a298-c0aa-4153-8d72-a02b997ba0ee"),
        name="Recruit helpers",
        signal=SignalNameEnum.recruit_helpers,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Time to Recruit Helpers for workshop at {{ event.venue }}",
        body=(
            "Hey everyone, please remember to seek helpers for the workshop "
            "{{ event.slug }} -Best, {{ assignee.full_name }}."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("e4a39483-590b-44e0-93cb-e3d403d15d8f"),
        name="Post Workshop 7 days",
        signal=SignalNameEnum.post_workshop_7days,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Completed workshop at {{ event.venue }} on {{ event.human_dates }} ({{ event.slug }})",
        body="Thank you for hosting and teaching the workshop at {{ event.venue }} (({{ event.slug }})!",
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("2f0058b5-cfc6-420c-90e5-2b8160eab7ec"),
        name="New Self-Organised Workshop",
        signal=SignalNameEnum.new_self_organised_workshop,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="{{ workshop_host.fullname }} ({{ event.slug }}) Workshop",
        body=(
            "Thanks for your Self-Organised workshop submission at {{ event.venue }} on"
            " {{ event.human_readable_date }}. Your workshop has been added to our "
            "database."
        ),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("1b7cff0e-5102-4c88-9bd5-efba57078580"),
        name="Ask for website",
        signal=SignalNameEnum.ask_for_website,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Workshop Website needed for workshop at {{ event.venue }} on {{ event.human_readable_date }}",
        body=("This is a friendly reminder to please share with me the workshop website once it has been completed."),
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("c176fd82-67bc-4ea7-bd0f-f28a368325ae"),
        name="Membership Quarterly Email (3 months after start)",
        signal=SignalNameEnum.membership_quarterly_3_months,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Membership Quarterly Email (3 months after start)",
        body="""Dear {% for contact in members_contacts %} {{ contact.personal }},{% endfor %}

You are now 3 months into your Carpentries membership which runs from {{ membership.agreement_start }}
to {{ membership.agreement_end }}. We would like to share this update with you.

{% if membership.workshops_without_admin_fee_total_allowed > 0 %}
**Workshops**
To date you have used {{ membership.workshops_without_admin_fee_completed +
membership.workshops_without_admin_fee_planned }} of your
{{ membership.workshops_without_admin_fee_total_allowed }} workshops.  You have
{{ membership.workshops_without_admin_fee_remaining }} workshops left.
Include other general workshops text here.
{% endif %}
{% if membership.workshops_without_admin_fee_completed +
membership.workshops_without_admin_fee_planned >= 1 %}
{% for event in events %}
* [{{ event.slug }}]({{ event.url }})
{% endfor %}
{% endif %}

{% if membership.public_instructor_training_seats_total + membership.inhouse_instructor_training_seats_total >= 1%}
**Instructor Training**
To date you have used
{{ membership.public_instructor_training_seats_utilized + membership.inhouse_instructor_training_seats_utilized }} of
your {{ membership.public_instructor_training_seats_total + membership.inhouse_instructor_training_seats_total }}
instructor training seats and have
{{ membership.public_instructor_training_seats_remaining + membership.inhouse_instructor_training_seats_remaining }}
instructor training seats remaining.  Include other general instructor training text here.
{% endif %}

{% if membership.public_instructor_training_seats_utilized + membership.inhouse_instructor_training_seats_utilized >= 1 %}
{% for task in trainee_tasks %}
* {{ task.person.full_name }}
{% endfor %}
{% endif %}

Here is a closing paragraph with other general information.  Please contact us with any questions.
The Carpentries Membership Team
""",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("9876ff94-74fa-4bd8-ae47-df697c3f3826"),
        name="Membership Quarterly Email (6 months after start)",
        signal=SignalNameEnum.membership_quarterly_6_months,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Membership Quarterly Email (6 months after start)",
        body="""Dear {% for contact in members_contacts %} {{ contact.personal }},{% endfor %}

You are now 6 months into your Carpentries membership which runs from {{ membership.agreement_start }}
to {{ membership.agreement_end }}. We would like to share this update with you.

{% if membership.workshops_without_admin_fee_total_allowed > 0 %}
**Workshops**
To date you have used {{ membership.workshops_without_admin_fee_completed +
membership.workshops_without_admin_fee_planned }} of your
{{ membership.workshops_without_admin_fee_total_allowed }} workshops.  You have
{{ membership.workshops_without_admin_fee_remaining }} workshops left.
Include other general workshops text here.
{% endif %}
{% if membership.workshops_without_admin_fee_completed +
membership.workshops_without_admin_fee_planned >= 1 %}
{% for event in events %}
* [{{ event.slug }}]({{ event.url }})
{% endfor %}
{% endif %}

{% if membership.public_instructor_training_seats_total + membership.inhouse_instructor_training_seats_total >= 1%}
**Instructor Training**
To date you have used
{{ membership.public_instructor_training_seats_utilized + membership.inhouse_instructor_training_seats_utilized }} of
your {{ membership.public_instructor_training_seats_total + membership.inhouse_instructor_training_seats_total }}
instructor training seats and have
{{ membership.public_instructor_training_seats_remaining + membership.inhouse_instructor_training_seats_remaining }}
instructor training seats remaining.  Include other general instructor training text here.
{% endif %}

{% if membership.public_instructor_training_seats_utilized + membership.inhouse_instructor_training_seats_utilized >= 1 %}
{% for task in trainee_tasks %}
* {{ task.person.full_name }}
{% endfor %}
{% endif %}

Here is a closing paragraph with other general information.  Please contact us with any questions.
The Carpentries Membership Team
""",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        id=UUID("7a943d4f-7cd1-480e-80f5-9febd25a47b5"),
        name="Membership Quarterly Email (3 months before end)",
        signal=SignalNameEnum.membership_quarterly_9_months,
        from_header="workshops@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Membership Quarterly Email (3 months before end)",
        body="""Dear {% for contact in members_contacts %} {{ contact.personal }},{% endfor %}

Your Carpentries membership which runs from {{ membership.agreement_start }} to {{ membership.agreement_end }} will be
expiring soon. Here is an update and information on how to renew.  Include general renewal information here.

{% if membership.workshops_without_admin_fee_total_allowed > 0 %}
**Workshops**
To date you have used {{ membership.workshops_without_admin_fee_completed +
membership.workshops_without_admin_fee_planned }} of your
{{ membership.workshops_without_admin_fee_total_allowed }} workshops.  You have
{{ membership.workshops_without_admin_fee_remaining }} workshops left.
Include other general workshops text here.
{% endif %}
{% if membership.workshops_without_admin_fee_completed +
membership.workshops_without_admin_fee_planned >= 1 %}
{% for event in events %}
* [{{ event.slug }}]({{ event.url }})
{% endfor %}
{% endif %}

{% if membership.public_instructor_training_seats_total + membership.inhouse_instructor_training_seats_total >= 1%}
**Instructor Training**
To date you have used
{{ membership.public_instructor_training_seats_utilized + membership.inhouse_instructor_training_seats_utilized }} of
your {{ membership.public_instructor_training_seats_total + membership.inhouse_instructor_training_seats_total }}
instructor training seats and have
{{ membership.public_instructor_training_seats_remaining + membership.inhouse_instructor_training_seats_remaining }}
instructor training seats remaining.  Include other general instructor training text here.
{% endif %}

{% if membership.public_instructor_training_seats_utilized + membership.inhouse_instructor_training_seats_utilized >= 1 %}
{% for task in trainee_tasks %}
* {{ task.person.full_name }}
{% endfor %}
{% endif %}

Here is a closing paragraph with other general information.  Please contact us with any questions.
The Carpentries Membership Team
""",  # noqa: E501
    ),
]


def email_template_transform(email_template_def: dict[str, Any]) -> EmailTemplate:
    return EmailTemplate(**email_template_def)


def run() -> None:
    seed_models(EmailTemplate, cast(list[dict[str, Any]], EMAIL_TEMPLATES), "signal", email_template_transform, logger)

    deprecate_models(EmailTemplate, DEPRECATED_EMAIL_TEMPLATES, "id", logger)
