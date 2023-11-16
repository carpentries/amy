from django import template
from django.db.models import Model

from emails.models import ScheduledEmailStatus, ScheduledEmailStatusActions

register = template.Library()


@register.filter
def model_documentation_link(model: Model) -> str:
    # This is a limited mapping of model to its documentation link. It should
    # be expanded as needed.
    # If our model documentation grows, we should consider including link to model
    # documentation inside every model. Then this mapping would become obsolete.
    mapping = {
        "InstructorRecruitmentSignup": (
            "https://carpentries.github.io/amy/design/database_models/"
            "#instructorrecruitmentsignup"
        ),
        "Event": "https://carpentries.github.io/amy/amy_database_structure/#events",
        "Award": "https://carpentries.github.io/amy/design/database_models/#award",
        "Person": "https://carpentries.github.io/amy/amy_database_structure/#persons",
    }
    model_name = model.__class__.__name__
    return mapping.get(model_name, "")


@register.simple_tag
def allowed_actions_for_status(status: ScheduledEmailStatus) -> list[str]:
    return [
        key
        for key, statuses in ScheduledEmailStatusActions.items()
        if status in statuses
    ]
