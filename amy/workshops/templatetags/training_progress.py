from django import template
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe

from workshops.models import TrainingProgress

register = template.Library()


@register.simple_tag
def progress_label(progress):
    assert isinstance(progress, TrainingProgress)

    if progress.discarded:
        additional_label = "dark"

    else:
        switch = {
            "n": "warning",
            "f": "danger",
            "a": "warning",
            "p": "success",
        }
        additional_label = switch[progress.state]

    fmt = "badge badge-{}".format(additional_label)
    return mark_safe(fmt)


@register.simple_tag
def progress_description(progress):
    assert isinstance(progress, TrainingProgress)

    text = "{discarded}{state} {type}<br />{evaluated_by}<br />on {day}.{notes}".format(
        discarded="discarded " if progress.discarded else "",
        state=progress.get_state_display(),
        type=progress.requirement,
        evaluated_by=(
            "evaluated by {}".format(progress.evaluated_by.full_name)
            if progress.evaluated_by is not None
            else "submitted"
        ),
        day=progress.created_at.strftime("%A %d %B %Y at %H:%M"),
        notes="<br />Notes: {}".format(escape(progress.notes))
        if progress.notes
        else "",
    )
    text = text[0].upper() + text[1:]
    return mark_safe(text)
