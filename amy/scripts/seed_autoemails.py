import logging
from typing import Callable, TypedDict, cast

from django.db.models import Model

from autoemails.models import EmailTemplate, Trigger
from workshops.models import Tag
from workshops.utils.seeding import deprecate_models, seed_models

logger = logging.getLogger("amy")

# If an entry needs to be removed from the database, remove it from e.g.
# `EMAIL_TEMPLATES`, and put its' ID in `DEPRECATED_EMAIL_TEMPLATES`.

DEPRECATED_TAGS: list[str] = []
DEPRECATED_EMAIL_TEMPLATES: list[str] = []
DEPRECATED_TRIGGERS: list[str] = []

TagDef = TypedDict("TagDef", {"name": str, "details": str, "priority": int})
EmailTemplateDef = TypedDict(
    "EmailTemplateDef",
    {
        "active": bool,
        "slug": str,
        "subject": str,
        "to_header": str,
        "from_header": str,
        "cc_header": str,
        "bcc_header": str,
        "reply_to_header": str,
        "body_template": str,
    },
)
TriggerDef = TypedDict("TriggerDef", {"action": str, "template_slug": str, "active": bool})

TAGS: list[TagDef] = [
    TagDef(name="automated-email", details="Only for EMAIL AUTOMATION", priority=0),
]

EMAIL_TEMPLATES: list[EmailTemplateDef] = [
    EmailTemplateDef(
        active=True,
        slug="confirming-instructing-workshop",
        subject="Confirmation of your participation as an instructor for {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop organized by {{ host.fullname }} {% if dates %} ({{ dates }}){% endif %}",  # noqa: E501
        to_header="{{ instructor.email }}",
        from_header="no-reply@carpentries.org",
        cc_header="",
        bcc_header="amy-auto-emails@carpentries.org",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template="Hi {{instructor.personal}},\r\n\r\nThank you for volunteering to teach! You are confirmed to teach a workshop at {{ host.fullname }}{% if dates %} ({{ dates }}){% endif %}.\r\n\r\n{% if \"online\" in tags %}\r\nWe\u2019ll be following up shortly to introduce you to your host and your co-instructor. As you prepare to teach this online workshop, be sure to review our [online workshop resources](https://docs.carpentries.org/resources/workshops/resources_for_online_workshops.html) in our handbook.   Please let me know if you have any other questions, and we're looking forward to working with you on this workshop!\r\n\r\n{% else %}\r\nWe\u2019ll be following up shortly to introduce you to your host and your co-instructor. Your host will be the best resource for planning travel arrangements. Please let me know if you have any other questions, and we're looking forward to working with you on this workshop!\r\n\r\n{% endif %}\r\n\r\n\r\nThanks for all you do!\r\n\r\nBest,  \r\n{{ assignee }}",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="7days-post-workshop",
        subject="Completed {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }} on {{ dates }}",  # noqa: E501
        to_header="{# This gets overwritten anyway #}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="amy-auto-emails@carpentries.org",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template='Thank you for teaching the workshop at {{ workshop.venue }}! We appreciate the dedication you\u2019ve shown to help spread data management and computational programming skills and the hard work you put into preparing for your workshop.\r\n\r\n{% if "online" in tags %}\r\nPlease take a moment to [provide feedback](https://docs.google.com/forms/d/1qf-SRoHg9plaqifkln6PBn__qVqGoKbNSLrn9m0LYJI/edit ) from your online teaching experience. \r\n{% endif %}\r\n\r\nWe want to be sure to give credit to all of our instructors and helpers in our database.\r\n\r\nWe currently have these instructors listed:\r\n\r\n{% for instructor_task in workshop.task_set.instructors %}\r\n* {{ instructor_task.person }}\r\n{% endfor %}\r\n\r\n{% if helpers %}We currently have these helpers listed:\r\n\r\n{% for helper in helpers %}\r\n* {{ helper }}{% endfor %}\r\n\r\n{% else %}\r\nWe don\u2019t have the names of any of your helpers.\r\n{% endif %}\r\n\r\nIf the names for the instructors or the helpers are not accurate, please make sure they are up-to-date on your workshop website and we will retrieve the information from there in a few days.\r\n\r\nHere is the link to review the pre and post survey responses. If you would like to download the data, you\'ll see a link to do so at the bottom right of the survey results page if there are at least 10 answers. As a reminder, please do not share this link publicly:\r\n\r\n*  {{ reports_link }}\r\n\r\nFeel free to join one of the weekly instructor discussion sessions whenever you are available. In these discussion sessions, you can share your feedback, ask questions, and hear from other instructors. Check out the calendar [here](https://pad.carpentries.org/community-discussions), and be sure to check your timezone when you sign up. \r\n\r\nIf you have any questions regarding anything I\u2019ve shared do not hesitate to email me directly. Thanks for all of your hard work running this workshop, and for everything you do with The Carpentries!\r\n\r\nBest,  \r\n{{ assignee }}',  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="self-organised-request",
        subject="{{ workshop.host.fullname }} ({{ workshop.slug }}) Workshop",
        to_header="{# This gets overwritten anyway #}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="amy-auto-emails@carpentries.org",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template='Hi {{ request.personal }}, \r\n\r\nThanks for your self-organized workshop submission at {{ workshop.venue }} on {{ dates }}. Your workshop has been added to the database and should appear on the website in a few hours. We know that there are several things to think about when preparing to teach a Carpentries workshop, so we\u2019ve included some reminders below:\r\n\r\n* **Helpers:** If possible, recruit some helpers. Helpers do not have to be affiliated with [The Carpentries](https://carpentries.org/), and actually being a helper is a great way to introduce others to The Carpentries. In order to assist you, we have developed text for you to use to recruit potential [helpers](https://docs.carpentries.org/resources/workshops/email_templates.html#recruiting-helpers). \r\n* **Survey Links:** The learner facing survey links are automatically generated on the [workshop\'s webpage]({{ workshop.url }}). They will be located directly above and within the schedule. You are welcome to share the survey links (located on the workshop webpage) with your attendees whenever the time is right for your workshop. \r\n{% if "online" in tags %}\r\n* **Online Teaching:** If you plan to teach/host a workshop online please check out our recommendations for online resources in [our handbook](https://docs.carpentries.org/resources/workshops/resources_for_online_workshops.html). This official set of recommendations will be updated as we receive feedback from the community. We would welcome [any feedback](https://forms.gle/iKLCdSkzqiHTY2yu5) you may have after teaching online.\r\n{% endif %}\r\n\r\n{% if short_notice %}\r\nPlease allow a few days to return the links to view the results of the survey.  \r\nFeel free to follow-up if you have any questions or concerns. \r\n{% else %}\r\nI will send out the links to view the results of the survey approximately 1 week prior to the workshop.\r\n{% endif %}\r\n\r\nPlease let me know if you have any questions or concerns.  \r\n\r\nBest,  \r\n{{ assignee }}',  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="instructors-host-introduction",
        subject="Instructors for {{ workshop_main_type }} workshop at {{ workshop.venue }} on {{ dates }}",  # noqa: E501
        to_header="{# This gets overwritten anyway #}",
        from_header="webmaster@localhost",
        cc_header="",
        bcc_header="",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template='Hi everyone,\r\n\r\n{% if "online" in tags %}\r\nThis email is to introduce {{ host.full_name }} of {{ workshop.venue }} with instructors {{ instructor1.full_name }}, {{ instructor2.full_name }}, {{ supporting_instructor1.full_name }} and {{ supporting_instructor2.full_name }}. They will be teaching an online {{ workshop_main_type }} workshop on {{ dates }}.\r\n{% else %}\r\nThis email is to introduce {{ host.full_name }} of {{ workshop.venue }} with instructors {{ instructor1.full_name }} and {{ instructor2.full_name }}. They will be teaching a {{ workshop_main_type }} workshop on {{ dates }}.\r\n{% endif %}\r\n\r\nI am {{ assignee }} and I will be supporting all of the logistical details with this workshop.\r\n\r\nNext steps:\r\n\r\n{% if "online" not in tags %}\r\nInstructors will work directly with {{ host.personal }} to make travel arrangements. We are not part of this process. This may include airfare, ground travel, hotel, and meals/incidentals. {{ host.personal }}, it is up to you whether you want to book things directly or have instructors make their own arrangements and get reimbursed. Either way, please keep in mind our instructors are volunteering two days of their time to teach with you, so please support them in making travel and reimbursement as smooth as possible.\r\n{% endif %}\r\n\r\nYou can all read more about the roles of workshop hosts, instructors, and helpers [here](https://docs.carpentries.org/resources/workshops/checklists.html). I\u2019ll highlight a few things here.\r\n\r\n{{ host.personal }}, can you share a little about who your learners are and what you and they are expecting? That will help our instructors be prepared. We also like to have a couple of helpers at each workshop from the local community. Would you be able to help secure a couple of helpers? They don\u2019t need to be connected with us; they just need a good understanding of the technologies we teach and an enthusiasm to help others. {% if "online" in tags %}[Here](https://docs.carpentries.org/resources/workshops/checklists.html) are the recommended responsibilities for helpers during online workshops.{% endif %}\r\n\r\n{% if "online" in tags %}\r\n{{ instructor1.personal }}, {{ instructor2.personal }}, {{ supporting_instructor1.personal }} and {{ supporting_instructor2.personal }}, please feel free to introduce yourselves and share a bit about your backgrounds. We value the background and expertise you bring to this, and want to hear about you.\r\n{% else %}\r\n{{ instructor1.personal }} and {{ instructor2.personal }}, please feel free to introduce yourselves and share a bit about your backgrounds. We value the background and expertise you bring to this, and want to hear about you.\r\n{% endif %}\r\n\r\n{{ instructor1.personal }} and {{ instructor2.personal }} will divide up the [curriculum]({% if workshop_main_tag == \'SWC\' %}https://software-carpentry.org/lessons/{% elif workshop_main_tag == \'DC\' %}http://www.datacarpentry.org/lessons/{% elif workshop_main_tag == \'LC\' %}https://librarycarpentry.org/lessons/{% endif %}) to know who\u2019s teaching what. One of them will create the workshop\u2019s web page on GitHub, which will include workshop details and instructions on what learners will need to install on their computers. The template can be found [here](https://github.com/carpentries/workshop-template).\r\n\r\nPlease use the workshop id: {{ workshop.slug }}.\r\n\r\n{{ host.personal }}, if you want to handle registration internally that\u2019s fine. Otherwise I can work with you to create an Eventbrite registration page. I will need to know a total count, the registration fee (if any, as well as a refund policy), and the exact location. Regardless, all learners should complete pre/post workshop surveys which will be available on the web page the instructors create. I will share links so you all can view survey results.\r\n\r\nI will check in over the next few weeks and after it\u2019s all over to hear how it went. Any of you are also welcome to join our instructor discussion sessions before and/or after the workshop. It\u2019s a great way to ask questions and share ideas with other instructors before you teach, and to give us feedback after you teach. Check out the schedule and sign up [here](https://pad.carpentries.org/community-discussions). \r\n\r\nWe are so glad to have everyone confirmed for this. Please email any questions you all may have for us or each other.\r\n\r\nThanks so much!\r\n\r\nBest,\r\n{{ assignee }}',  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="confirming-supporting-instructing-workshop",
        subject="Confirmation of your participation as a Supporting-Instructor for {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop @ {{ workshop.venue }} {% if dates %}({{ dates }}){% endif %}",  # noqa: E501
        to_header="{{ instructor.email }}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="amy-auto-emails@carpentries.org",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template="Hi {{ instructor.personal }},\r\n\r\nThank you for volunteering to teach! You are confirmed to teach a workshop at {{ host.fullname }}{% if dates %} ({{ dates }}){% endif %}.\r\n\r\n{% if \"online\" in tags %}\r\nWe\u2019ll be following up shortly to introduce you to your host and your co-instructor. As you prepare to teach this online workshop, be sure to review our [online workshop resources](https://docs.carpentries.org/resources/workshops/resources_for_online_workshops.html) in our handbook. Please let me know if you have any other questions, and we're looking forward to working with you on this workshop!\r\n\r\n{% else  %}\r\nWe\u2019ll be following up shortly to introduce you to your host and your co-instructor. Your host will be the best resource for planning travel arrangements. Please let me know if you have any other questions, and we're looking forward to working with you on this workshop!\r\n\r\n{% endif %}\r\n\r\nThanks for all you do!\r\n\r\nBest,\r\n{{ assignee }}",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="ask-for-website",
        subject="Workshop Website needed for {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }} {% if dates %} on {{ dates }}{% endif %}",  # noqa: E501
        to_header="{# This gets overwritten anyway #}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="",
        reply_to_header="{regional coordinator assigned to WRF}",
        body_template="Hi {% for person in instructors %}{{ person.full_name }}, {% endfor %}\r\n\r\nThis is a friendly reminder to please share with me the workshop website once it has been completed. \r\n\r\nHere is the [template](https://github.com/carpentries/workshop-template) for guidance. Please use the workshop id: {{ event.slug }}\r\n\r\nPlease let me know if you have any questions,\r\n\r\nBest, {{ assignee }}",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="request-review1-less-than-2-months",
        subject="Processed/Reviewed {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }} {% if dates %} on {{ dates }}{% endif %}",  # noqa: E501
        to_header="{{ request.email }}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="amy-auto-emails@carpentries.org",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template="Hi {{ request.personal }},\r\n\r\nThank you! We have received your request for a Carpentries Workshop. We ask that you provide us 2-3 months advance notice of a workshop to allow sufficient time to organise a workshop. The dates you have provided are outside of our normal recruitment timeline. I will begin recruiting instructors immediately, however I cannot guarantee that we can secure instructors in time for your requested dates. Please let us know if you have flexibility with your dates.\r\n\r\nIf the instructors are confirmed, you will receive an introduction email that will explain the next steps. If instructors are not confirmed within 3 weeks, we will need to look at other dates.  Please let me know if you have any questions or concerns.\r\n\r\nBest, {{ assignee }}",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="request-review2-2-to-3-months",
        subject="Processed/Reviewed {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }} {% if dates %} on {{ dates }}{% endif %}",  # noqa: E501
        to_header="{{ request.email }}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="amy-auto-emails@carpentries.org",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template="Hi {{ request.personal }},\r\n\r\nThank you! We have received your request for a Carpentries Workshop. We will begin recruiting instructors immediately. Once they are confirmed, you will receive an introduction email that will explain the next steps. Please let me know if you have any questions or concerns.\r\n\r\nBest, {{ assignee }}",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="request-review3-over-3-months",
        subject="Processed/Reviewed {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }} {% if dates %} on {{ dates }}{% endif %}",  # noqa: E501
        to_header="{{ request.email }}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="amy-auto-emails@carpentries.org",
        reply_to_header="{{ regional_coordinator_email.0 }}",
        body_template="Hi {{ request.personal }},\r\n\r\nThank you! We have received your request for a Carpentries Workshop. We will begin recruiting instructors around { CHANGE ME: date_start_workshop - 2 months }. Once the instructors are confirmed we will let you know via email and we will explain the next steps. Please let me know if you have any questions or concerns.\r\n\r\nBest, {{ assignee }}",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="recruit-helpers",
        subject="Time to Recruit Helpers for {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }} {% if dates %} on {{ dates }}{% endif %}",  # noqa: E501
        to_header="{# This gets overwritten anyway #}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="{{ regional_coordinator_email.0 }}",
        reply_to_header="",
        body_template='Hi Everyone, \r\n\r\nWe know that there are several things to think about when preparing to teach a Carpentries workshop. With approximately 3 weeks until your {% if workshop_main_type %}{{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }} {% if dates %} on {{ dates }}{% endif %}, you should begin thinking about recruiting [helpers](https://docs.carpentries.org/resources/workshops/checklists.html). In order to assist you, we have developed text for you to use to recruit potential helpers. Remember, Helpers do not have to be affiliated with [The Carpentries](https://carpentries.org/).\r\n\r\n{% if "online" in tags %}\r\nBe sure to review the recommended ways to [utilise the Helpers](hhttps://docs.carpentries.org/resources/workshops/resources_for_online_workshops.html) for online workshops.\r\n{% endif %}\r\n\r\nPlease let us know if you have any questions.\r\n{{ assignee }}',  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="consents-new",
        subject="New Terms Available",
        to_header="{{ request.email }}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="",
        reply_to_header="",
        body_template="A new term is available to consent to. Please [sign in](https://carpentries.org/) to consent to it.",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="profile-update",
        subject="The Carpentries Profile Update Reminder",
        to_header="{{ request.email }}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="",
        reply_to_header="",
        body_template="Dear {{ person_full_name }},\r\n\r\nOnce a year, we ask you to check that the information we store about you and your activities with The Carpentries are up-to-date. It is important that we have current information so we can inform you of new teaching or volunteering opportunities.\r\n\r\nPlease go to <https://amy.carpentries.org> to log in to your AMY account. Check that your email address and affiliation are current, that your knowledge domain and the lessons you can teach are current, and that all the workshops you have taught are reflected on your profile. If you need help updating your profile, do not hesitate to contact us at [team@carpentries.org](mailto:team@carpentries.org).\r\n\r\nThank you for everything you do with The Carpentries!\r\n\r\nSincerely,\r\nThe Carpentries\r\n\r\n\r\n\r\nYou are receiving this message because your email address was provided for this AMY account. Please note that this email is a legal notice, and you cannot unsubscribe. If you believe you received this message in error, do not hesitate to contact [team@carpentries.org](mailto:team@carpentries.org).",  # noqa: E501
    ),
    EmailTemplateDef(
        active=True,
        slug="declined-instructor-signups",
        subject="Thank you for signing up to teach at{% if workshop_main_type %} {{ workshop_main_type }}{% endif %} workshop at {{ workshop.venue }}{% if dates %} on {{ dates }}{% endif %}",  # noqa: E501
        to_header="{{ email }}",
        from_header="amy-no-reply@carpentries.org",
        cc_header="",
        bcc_header="",
        reply_to_header="",
        body_template="Thank you for your interest in {{ workshop.slug }}. Unfortunately we have placed other Instructors.",  # noqa: E501
    ),
]

TRIGGERS: list[TriggerDef] = [
    {
        "action": "new-instructor",
        "template_slug": "confirming-instructing-workshop",
        "active": True,
    },
    {
        "action": "week-after-workshop-completion",
        "template_slug": "7days-post-workshop",
        "active": True,
    },
    {
        "action": "self-organised-request-form",
        "template_slug": "self-organised-request",
        "active": True,
    },
    {
        "action": "instructors-host-introduction",
        "template_slug": "instructors-host-introduction",
        "active": True,
    },
    {
        "action": "new-supporting-instructor",
        "template_slug": "confirming-supporting-instructing-workshop",
        "active": True,
    },
    {
        "action": "ask-for-website",
        "template_slug": "ask-for-website",
        "active": True,
    },
    {
        "action": "workshop-request-response1",
        "template_slug": "request-review1-less-than-2-months",
        "active": True,
    },
    {
        "action": "workshop-request-response2",
        "template_slug": "request-review2-2-to-3-months",
        "active": True,
    },
    {
        "action": "workshop-request-response3",
        "template_slug": "request-review3-over-3-months",
        "active": True,
    },
    {
        "action": "consent-required",
        "template_slug": "consents-new",
        "active": True,
    },
    {
        "action": "profile-update",
        "template_slug": "profile-update",
        "active": True,
    },
    {
        "action": "declined-instructors",
        "template_slug": "declined-instructor-signups",
        "active": True,
    },
]

# --------------------------------------------------------------------------------------


def tag_transform(tag_def: dict) -> Tag:
    return Tag(**tag_def)


def email_template_transform(email_template_def: dict) -> EmailTemplate:
    return EmailTemplate(**email_template_def)


def trigger_transform(trigger_def: TriggerDef) -> Trigger:
    template = EmailTemplate.objects.get(slug=trigger_def["template_slug"])
    return Trigger(action=trigger_def["action"], active=trigger_def["active"], template=template)


def run() -> None:
    seed_models(Tag, TAGS, "name", tag_transform, logger)
    seed_models(EmailTemplate, EMAIL_TEMPLATES, "slug", email_template_transform, logger)
    seed_models(
        Trigger,
        TRIGGERS,
        "action",
        cast(Callable[[dict], Model], trigger_transform),
        logger,
    )

    deprecate_models(Trigger, DEPRECATED_TRIGGERS, "action", logger)
    deprecate_models(EmailTemplate, DEPRECATED_EMAIL_TEMPLATES, "slug", logger)
    deprecate_models(Tag, DEPRECATED_TAGS, "name", logger)
