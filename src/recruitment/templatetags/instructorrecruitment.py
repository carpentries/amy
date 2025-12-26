from collections.abc import Sequence
from datetime import timedelta

from django import template

from src.recruitment.models import (
    InstructorRecruitment,
    InstructorRecruitmentSignup,
    RecruitmentPriority,
)
from src.workshops.models import Event

register = template.Library()


@register.simple_tag
def get_event_conflicts(events_to_check: Sequence[Event], event: Event) -> list[Event]:
    conflicts: list[Event] = []

    # event must have start and end dates, otherwise we can't get conflicts
    if not (event.start and event.end):
        return conflicts

    for event_to_check in events_to_check:
        if event == event_to_check:
            continue

        # event getting checked must have start and end dates
        if not (event_to_check.start and event_to_check.end):
            continue

        if event.start <= event_to_check.end and event.end >= event_to_check.start:
            conflicts.append(event_to_check)

    return conflicts


@register.simple_tag
def get_events_nearby(
    events_to_check: Sequence[Event],
    event: Event,
    days_before: int = 14,
    days_after: int = 14,
) -> list[Event]:
    """Get events nearby another event time-wise."""
    nearby: list[Event] = []

    # event must have start and end dates, otherwise we can't get nearby events
    if not (event.start and event.end):
        return nearby

    for event_to_check in events_to_check:
        if event == event_to_check:
            continue

        # event getting checked must have start and end dates
        if not (event_to_check.start and event_to_check.end):
            continue

        if (
            event.start - timedelta(days=days_before) <= event_to_check.end
            and event.end + timedelta(days=days_after) >= event_to_check.start
        ):
            nearby.append(event_to_check)

    return nearby


@register.simple_tag
def get_signup_conflicts(
    signups_to_check: Sequence[InstructorRecruitmentSignup],
    recruitment: InstructorRecruitment,
) -> list[InstructorRecruitmentSignup]:
    conflicts: list[InstructorRecruitmentSignup] = []

    # recruitment event must have start and end dates, otherwise we can't get conflicts
    if not (recruitment.event.start and recruitment.event.end):
        return conflicts

    for signup_to_check in signups_to_check:
        if recruitment == signup_to_check.recruitment:
            continue

        # event getting checked must have start and end dates
        if not (signup_to_check.recruitment.event.start and signup_to_check.recruitment.event.end):
            continue

        if (
            recruitment.event.start <= signup_to_check.recruitment.event.end
            and recruitment.event.end >= signup_to_check.recruitment.event.start
        ):
            conflicts.append(signup_to_check)

    return conflicts


@register.filter
def priority_label(value: int | RecruitmentPriority) -> str:
    return RecruitmentPriority(value).label
