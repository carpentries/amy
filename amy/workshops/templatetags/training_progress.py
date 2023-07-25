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

    fmt = f"badge badge-{progress_state_class(progress.state)}"
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
    # we allow 90 days for checkout
    return start_date + timedelta(days=90)


@register.simple_tag
def progress_trainee_view(progress: TrainingProgress) -> str:
    assert isinstance(progress, TrainingProgress)

    # state: follow our internal choices
    # except for Welcome Session
    # as 'passed' implies assessment, but you just have to show up
    state_display = progress.get_state_display().lower()
    if state_display == "passed" and progress.requirement.name == "Welcome Session":
        state_display = "completed"

    # date: show event dates for training, most recent update date otherwise
    date = progress.event.end if progress.event else progress.last_updated_at

    # notes: show notes if state is failed or asked to repeat
    # TODO: implement a separate field for these notes
    # notes = (
    #     f"<p>Administrator comments: {progress.notes}</p>"
    #     if progress.state in ["f", "a"]
    #     else ""
    # )

    # put it all together
    text = (
        f'<p class="text-{progress_state_class(progress.state)}"> '
        f"{progress.requirement.name} {state_display} "
        f'as of {date.strftime("%B %d, %Y")}.</p>'
        # f'{notes}' # TODO
    )

    return mark_safe(text)
