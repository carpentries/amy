from datetime import datetime, timedelta

from django import template
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe

from workshops.models import TrainingProgress

register = template.Library()


@register.simple_tag
def progress_state_class(state):
    switch = {
        "n": "warning",
        "f": "danger",
        "a": "info",
        "p": "success",
    }
    return switch[state]


@register.simple_tag
def progress_label(progress: TrainingProgress):
    fmt = f"badge badge-{progress_state_class(progress.state)}"
    return mark_safe(fmt)


@register.simple_tag
def progress_description(progress: TrainingProgress):
    # build involvement details as needed
    if progress.requirement.name == "Get Involved" and progress.involvement_type:
        involvement = "<br />"
        involvement += progress.involvement_type.name
        if progress.involvement_type.name == "Other":
            involvement += (
                f": {escape(progress.trainee_notes) or 'No details provided'}"
            )
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
    # we allow 90 days for checkout
    return start_date + timedelta(days=90)


@register.simple_tag
def welcome_instructions(date: datetime | None = None):
    """Show different Etherpad links dependent on the time of year.

    From January to October, show just this year's Etherpad link.
    From November to December, show this year's and next year's Etherpad links.
    """
    if date is None:
        date = datetime.now()
    text = "<p>Register for a Welcome Session on "
    if date.month >= 11:
        text += (
            f"one of these Etherpads: "
            f'<a href="https://pad.carpentries.org/welcome-sessions-{ date.year }">'
            f"Welcome Sessions { date.year }</a>; "
            f'<a href="https://pad.carpentries.org/welcome-sessions-{ date.year+1 }">'
            f"Welcome Sessions { date.year+1 }</a>."
        )
    else:
        text += (
            f"this Etherpad: "
            f'<a href="https://pad.carpentries.org/welcome-sessions-{ date.year }">'
            f"Welcome Sessions { date.year }</a>."
        )
    text += "</p>"

    return mark_safe(text)
