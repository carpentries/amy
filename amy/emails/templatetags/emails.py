from django import template
from django.conf import settings
from django.db.models import Model

register = template.Library()


@register.simple_tag
def is_email_module_enabled() -> bool:
    try:
        return bool(settings.EMAIL_MODULE_ENABLED)
    except AttributeError:
        return False


@register.filter
def model_documentation_link(model: Model) -> str:
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
