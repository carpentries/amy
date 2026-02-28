import logging
from datetime import datetime
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from src.emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from src.emails.actions.base_strategy import run_strategy
from src.emails.models import ScheduledEmail, ScheduledEmailStatus
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
    Signal,
    instructor_declined_from_workshop_cancel_signal,
    instructor_declined_from_workshop_signal,
    instructor_declined_from_workshop_update_signal,
)
from src.emails.types import (
    InstructorDeclinedContext,
    InstructorDeclinedKwargs,
    StrategyEnum,
)
from src.emails.utils import api_model_url, immediate_action, log_condition_elements
from src.recruitment.models import InstructorRecruitmentSignup
from src.workshops.models import Event, Person, TagQuerySet

logger = logging.getLogger("amy")


def instructor_declined_from_workshop_strategy(
    signup: InstructorRecruitmentSignup,
) -> StrategyEnum:
    logger.info(f"Running InstructorDeclinedFromWorkshop strategy for {signup=}")

    signup_is_declined = signup.state == "d"
    person_email_exists = bool(signup.person.email)
    event = signup.recruitment.event
    carpentries_tags = event.tags.filter(name__in=TagQuerySet.CARPENTRIES_TAG_NAMES).exclude(
        name__in=TagQuerySet.NON_CARPENTRIES_TAG_NAMES
    )
    centrally_organised = event.administrator and event.administrator.domain != "self-organized"
    start_date_in_future = event.start and event.start >= timezone.now().date()

    log_condition_elements(
        signup=signup,
        signup_pk=signup.pk,
        signup_is_declined=signup_is_declined,
        event=event,
        person_email_exists=person_email_exists,
        carpentries_tags=carpentries_tags,
        centrally_organised=centrally_organised,
        start_date_in_future=start_date_in_future,
    )

    email_should_exist = (
        signup_is_declined and person_email_exists and carpentries_tags and centrally_organised and start_date_in_future
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(InstructorRecruitmentSignup)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=signup.pk,
        template__signal=INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
        state=ScheduledEmailStatus.SCHEDULED,
    ).exists()
    logger.debug(f"{email_exists=}")

    if not email_exists and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_exists and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif email_exists and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"InstructorDeclinedFromWorkshop strategy {result=}")
    return result


def run_instructor_declined_from_workshop_strategy(
    strategy: StrategyEnum,
    request: HttpRequest,
    signup: InstructorRecruitmentSignup,
    **kwargs: Any,
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_declined_from_workshop_signal,
        StrategyEnum.UPDATE: instructor_declined_from_workshop_update_signal,
        StrategyEnum.CANCEL: instructor_declined_from_workshop_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=signup,
        signup=signup,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[InstructorDeclinedKwargs]) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[InstructorDeclinedKwargs],
) -> InstructorDeclinedContext:
    person = Person.objects.get(pk=kwargs["person_id"])
    event = Event.objects.get(pk=kwargs["event_id"])
    instructor_recruitment_signup = InstructorRecruitmentSignup.objects.get(
        pk=kwargs["instructor_recruitment_signup_id"]
    )
    return {
        "person": person,
        "event": event,
        "instructor_recruitment_signup": instructor_recruitment_signup,
    }


def get_context_json(context: InstructorDeclinedContext) -> ContextModel:
    return ContextModel(
        {
            "person": api_model_url("person", context["person"].pk),
            "event": api_model_url("event", context["event"].pk),
            "instructor_recruitment_signup": api_model_url(
                "instructorrecruitmentsignup",
                context["instructor_recruitment_signup"].pk,
            ),
        },
    )


def get_generic_relation_object(
    context: InstructorDeclinedContext,
    **kwargs: Unpack[InstructorDeclinedKwargs],
) -> InstructorRecruitmentSignup:
    return context["instructor_recruitment_signup"]


def get_recipients(
    context: InstructorDeclinedContext,
    **kwargs: Unpack[InstructorDeclinedKwargs],
) -> list[str]:
    person = context["person"]
    return [person.email] if person.email else []


def get_recipients_context_json(
    context: InstructorDeclinedContext,
    **kwargs: Unpack[InstructorDeclinedKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", context["person"].pk),
                property="email",
            )
        ],
    )


class InstructorDeclinedFromWorkshopReceiver(BaseAction):
    signal = instructor_declined_from_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorDeclinedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[InstructorDeclinedKwargs]) -> InstructorDeclinedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorDeclinedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> InstructorRecruitmentSignup:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorDeclinedFromWorkshopUpdateReceiver(BaseActionUpdate):
    signal = instructor_declined_from_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorDeclinedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[InstructorDeclinedKwargs]) -> InstructorDeclinedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorDeclinedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> InstructorRecruitmentSignup:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorDeclinedFromWorkshopCancelReceiver(BaseActionCancel):
    signal = instructor_declined_from_workshop_signal.signal_name

    def get_context(self, **kwargs: Unpack[InstructorDeclinedKwargs]) -> InstructorDeclinedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorDeclinedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> InstructorRecruitmentSignup:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorDeclinedContext,
        **kwargs: Unpack[InstructorDeclinedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


instructor_declined_from_workshop_receiver = InstructorDeclinedFromWorkshopReceiver()
instructor_declined_from_workshop_signal.connect(instructor_declined_from_workshop_receiver)
instructor_declined_from_workshop_update_receiver = InstructorDeclinedFromWorkshopUpdateReceiver()
instructor_declined_from_workshop_update_signal.connect(instructor_declined_from_workshop_update_receiver)
instructor_declined_from_workshop_cancel_receiver = InstructorDeclinedFromWorkshopCancelReceiver()
instructor_declined_from_workshop_cancel_signal.connect(instructor_declined_from_workshop_cancel_receiver)
