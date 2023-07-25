from datetime import timedelta

from django import template
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe

from workshops.models import TrainingProgress

register = template.Library()


def progress_state_class(state):
    switch = {
        "n": "warning",
        "f": "danger",
        "a": "info",
        "p": "success",
    }
    return switch[state]


@register.simple_tag
def progress_label(progress):
    assert isinstance(progress, TrainingProgress)

    additional_label = progress_state_class(progress.state)

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

    day = (
        progress.date.strftime("%A %d %B %Y")
        if progress.date
        else progress.created_at.strftime("%A %d %B %Y at %H:%M")
    )

    text = "{state} {type}{involvement}<br />on {day}.{notes}".format(
        state=progress.get_state_display(),
        type=progress.requirement,
        involvement=involvement,
        day=day,
        notes="<br />Notes: {}".format(escape(progress.notes))
        if progress.notes
        else "",
    )
    text = text[0].upper() + text[1:]
    return mark_safe(text)


@register.simple_tag
def checkout_deadline(start_date):
    """get the year after the current year"""

    return start_date + timedelta(days=90)


@register.simple_tag
def progress_trainee_view(progress):
    assert isinstance(progress, TrainingProgress)

    date = progress.event.end if progress.event else progress.last_updated_at
    notes = (
        f"<p>Administrator comments: {progress.notes}</p>"
        if progress.state in ["f", "a"]
        else ""
    )

    text = (
        f'<p class="text-{progress_state_class(progress.state)}"> '
        f"{progress.requirement.name} {progress.get_state_display().lower()} "
        f'as of {date.strftime("%B %d, %Y")}.</p>{notes}'
    )

    return mark_safe(text)
