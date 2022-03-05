from datetime import timedelta
from typing import Sequence

from django import template
from django.conf import settings

from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.models import Event

register = template.Library()


@register.simple_tag
def is_instructor_recruitment_enabled() -> bool:
    try:
        return bool(settings.INSTRUCTOR_RECRUITMENT_ENABLED)
    except AttributeError:
        return False


@register.simple_tag
def get_event_conflicts(events: Sequence[Event], event: Event) -> list[Event]:
    conflicts: list[Event] = []

    for event_to_check in events:
        if event == event_to_check:
            continue

        if event.start <= event_to_check.end and event.end >= event_to_check.start:
            conflicts.append(event_to_check)

    return conflicts


@register.simple_tag
def get_events_nearby(
    events: Sequence[Event], event: Event, days_before: int = 14, days_after: int = 14
) -> list[Event]:
    nearby: list[Event] = []

    for event_to_check in events:
        if event == event_to_check:
            continue

        if (
            event.start - timedelta(days=days_before) <= event_to_check.end
            and event.end + timedelta(days=days_after) >= event_to_check.start
        ):
            nearby.append(event_to_check)

    return nearby


@register.simple_tag
def get_signup_conflicts(
    signups: Sequence[InstructorRecruitmentSignup], recruitment: InstructorRecruitment
) -> list[InstructorRecruitmentSignup]:
    conflicts: list[InstructorRecruitmentSignup] = []

    for signup_to_check in signups:
        if recruitment == signup_to_check.recruitment:
            continue

        if (
            recruitment.event.start <= signup_to_check.recruitment.event.end
            and recruitment.event.end >= signup_to_check.recruitment.event.start
        ):
            conflicts.append(signup_to_check)

    return conflicts
