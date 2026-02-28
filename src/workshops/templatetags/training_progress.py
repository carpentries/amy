from datetime import date, timedelta

from django import template
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

from src.workshops.models import TrainingProgress

register = template.Library()


@register.simple_tag
def progress_state_class(state: str) -> str:
    switch = {
        "n": "warning",
        "f": "danger",
        "a": "info",
        "p": "success",
    }
    return switch[state]


@register.simple_tag
def progress_label(progress: TrainingProgress) -> SafeString:
    fmt = f"badge badge-{progress_state_class(progress.state)}"
    return mark_safe(fmt)


@register.simple_tag
def progress_description(progress: TrainingProgress) -> str:
    # build involvement details as needed
    if progress.requirement.name == "Get Involved" and progress.involvement_type:
        involvement = "<br />"
        involvement += progress.involvement_type.name
        if progress.involvement_type.name == "Other":
            involvement += f": {escape(progress.trainee_notes) or 'No details provided'}"
    else:
        involvement = ""

    day = (
        progress.date.strftime("%A %d %B %Y") if progress.date else progress.created_at.strftime("%A %d %B %Y at %H:%M")
    )

    text = "{state} {type}{involvement}<br />on {day}.{notes}".format(
        state=progress.get_state_display(),
        type=progress.requirement,
        involvement=involvement,
        day=day,
        notes=f"<br />Notes: {escape(progress.notes)}" if progress.notes else "",
    )
    text = text[0].upper() + text[1:]
    return text


@register.simple_tag
def checkout_deadline(start_date: date) -> date:
    # we allow 90 days for checkout
    return start_date + timedelta(days=90)
