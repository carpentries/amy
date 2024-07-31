from datetime import datetime
import logging

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from typing_extensions import Unpack

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.models import ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import (
    INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
    Signal,
    instructor_badge_awarded_cancel_signal,
    instructor_badge_awarded_signal,
    instructor_badge_awarded_update_signal,
)
from emails.types import (
    InstructorBadgeAwardedContext,
    InstructorBadgeAwardedKwargs,
    StrategyEnum,
)
from emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    scalar_value_none,
)
from workshops.models import Award, Person

logger = logging.getLogger("amy")


def instructor_badge_awarded_strategy(award: Award, person: Person) -> StrategyEnum:
    logger.info(f"Running InstructorBadgeAwarded strategy for {award=}")

    award_pk = getattr(award, "pk", None)
    award_exists = award is not None and award_pk is not None
    instructor_award = award is not None and award.badge.name == "instructor"

    log_condition_elements(award_exists=award_exists, instructor_award=instructor_award)

    email_should_exist = award_exists and instructor_award
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(person)
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=person.pk,
        template__signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
        state=ScheduledEmailStatus.SCHEDULED,
    ).exists()
    logger.debug(f"{has_email_scheduled=}")

    if not has_email_scheduled and email_should_exist:
        result = StrategyEnum.CREATE
    elif has_email_scheduled and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif has_email_scheduled and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"InstructorBadgeAwarded strategy {result = }")
    return result


def run_instructor_badge_awarded_strategy(
    strategy: StrategyEnum, request: HttpRequest, person: Person, **kwargs
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_badge_awarded_signal,
        StrategyEnum.UPDATE: instructor_badge_awarded_update_signal,
        StrategyEnum.CANCEL: instructor_badge_awarded_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=person,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[InstructorBadgeAwardedKwargs]) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> InstructorBadgeAwardedContext:
    person = Person.objects.get(pk=kwargs["person_id"])
    award = Award.objects.filter(pk=kwargs["award_id"]).first()
    return {
        "person": person,
        "award": award,
    }


def get_context_json(context: InstructorBadgeAwardedContext) -> ContextModel:
    award = context["award"]
    return ContextModel(
        {
            "person": api_model_url("person", context["person"].pk),
            "award": api_model_url("award", award.pk) if award else scalar_value_none(),
        },
    )


def get_generic_relation_object(
    context: InstructorBadgeAwardedContext,
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> Person:
    return context["person"]


def get_recipients(
    context: InstructorBadgeAwardedContext,
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> list[str]:
    person = context["person"]
    return [person.email] if person.email else []


def get_recipients_context_json(
    context: InstructorBadgeAwardedContext,
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            {
                "api_uri": api_model_url("person", context["person"].pk),
                "property": "email",
            },  # type: ignore
        ],
    )


class InstructorBadgeAwardedReceiver(BaseAction):
    signal = instructor_badge_awarded_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> InstructorBadgeAwardedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorBadgeAwardedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> Person:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorBadgeAwardedUpdateReceiver(BaseActionUpdate):
    signal = instructor_badge_awarded_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> InstructorBadgeAwardedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorBadgeAwardedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> Person:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorBadgeAwardedCancelReceiver(BaseActionCancel):
    signal = instructor_badge_awarded_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> InstructorBadgeAwardedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorBadgeAwardedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> Person:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


instructor_badge_awarded_receiver = InstructorBadgeAwardedReceiver()
instructor_badge_awarded_signal.connect(instructor_badge_awarded_receiver)

instructor_badge_awarded_update_receiver = InstructorBadgeAwardedUpdateReceiver()
instructor_badge_awarded_update_signal.connect(instructor_badge_awarded_update_receiver)

instructor_badge_awarded_cancel_receiver = InstructorBadgeAwardedCancelReceiver()
instructor_badge_awarded_cancel_signal.connect(instructor_badge_awarded_cancel_receiver)
