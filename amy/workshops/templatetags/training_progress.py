from django import template
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe

from workshops.models import TrainingProgress

register = template.Library()


@register.simple_tag
def progress_label(progress):
    assert isinstance(progress, TrainingProgress)

    switch = {
        "n": "warning",
        "f": "danger",
        "a": "info",
        "p": "success",
    }
    additional_label = switch[progress.state]

    fmt = "badge badge-{}".format(additional_label)
    return mark_safe(fmt)


@register.simple_tag
def progress_description(progress):
    assert isinstance(progress, TrainingProgress)

    # build involvement details as needed
    if progress.requirement.name == "Get Involved" and progress.involvement_type:
        involvement = "<br />"
        involvement += progress.involvement_type.name
        if progress.involvement_type.name == "Other":
            involvement += f": {progress.trainee_notes or 'No details provided'}"
    else:
        involvement = ""

    text = "{state} {type}{involvement}<br />on {day}.{notes}".format(
        state=progress.get_state_display(),
        type=progress.requirement,
        involvement=involvement,
        day=progress.created_at.strftime("%A %d %B %Y at %H:%M"),
        notes="<br />Notes: {}".format(escape(progress.notes))
        if progress.notes
        else "",
    )
    text = text[0].upper() + text[1:]
    return mark_safe(text)
