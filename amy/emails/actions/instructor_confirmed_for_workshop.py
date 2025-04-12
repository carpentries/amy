from datetime import datetime
import logging
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.models import ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
    Signal,
    instructor_confirmed_for_workshop_cancel_signal,
    instructor_confirmed_for_workshop_signal,
    instructor_confirmed_for_workshop_update_signal,
)
from emails.types import (
    InstructorConfirmedContext,
    InstructorConfirmedKwargs,
    StrategyEnum,
)
from emails.utils import api_model_url, immediate_action, log_condition_elements
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Event, Person, TagQuerySet

logger = logging.getLogger("amy")


def instructor_confirmed_for_workshop_strategy(
    signup: InstructorRecruitmentSignup,
) -> StrategyEnum:
    logger.info(f"Running InstructorConfirmedForWorkshop strategy for {signup=}")

    signup_is_accepted = signup.state == "a"
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
        signup_is_accepted=signup_is_accepted,
        event=event,
        person_email_exists=person_email_exists,
        carpentries_tags=carpentries_tags,
        centrally_organised=centrally_organised,
        start_date_in_future=start_date_in_future,
    )

    email_should_exist = (
        signup_is_accepted and person_email_exists and carpentries_tags and centrally_organised and start_date_in_future
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(InstructorRecruitmentSignup)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=signup.pk,
        template__signal=INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
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

    logger.debug(f"InstructorConfirmedForWorkshop strategy {result=}")
    return result


def run_instructor_confirmed_for_workshop_strategy(
    strategy: StrategyEnum,
    request: HttpRequest,
    signup: InstructorRecruitmentSignup,
    **kwargs: Any,
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_confirmed_for_workshop_signal,
        StrategyEnum.UPDATE: instructor_confirmed_for_workshop_update_signal,
        StrategyEnum.CANCEL: instructor_confirmed_for_workshop_cancel_signal,
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


def get_scheduled_at(**kwargs: Unpack[InstructorConfirmedKwargs]) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[InstructorConfirmedKwargs],
) -> InstructorConfirmedContext:
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


def get_context_json(context: InstructorConfirmedContext) -> ContextModel:
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
    context: InstructorConfirmedContext, **kwargs: Unpack[InstructorConfirmedKwargs]
) -> InstructorRecruitmentSignup:
    return context["instructor_recruitment_signup"]


def get_recipients(context: InstructorConfirmedContext, **kwargs: Unpack[InstructorConfirmedKwargs]) -> list[str]:
    person = context["person"]
    return [person.email] if person.email else []


def get_recipients_context_json(
    context: InstructorConfirmedContext,
    **kwargs: Unpack[InstructorConfirmedKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", context["person"].pk),
                property="email",
            )
        ],
    )


class InstructorConfirmedForWorkshopReceiver(BaseAction):
    signal = instructor_confirmed_for_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorConfirmedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[InstructorConfirmedKwargs]) -> InstructorConfirmedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorConfirmedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> InstructorRecruitmentSignup:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorConfirmedForWorkshopUpdateReceiver(BaseActionUpdate):
    signal = instructor_confirmed_for_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorConfirmedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[InstructorConfirmedKwargs]) -> InstructorConfirmedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorConfirmedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> InstructorRecruitmentSignup:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorConfirmedForWorkshopCancelReceiver(BaseActionCancel):
    signal = instructor_confirmed_for_workshop_signal.signal_name

    def get_context(self, **kwargs: Unpack[InstructorConfirmedKwargs]) -> InstructorConfirmedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorConfirmedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> InstructorRecruitmentSignup:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


instructor_confirmed_for_workshop_receiver = InstructorConfirmedForWorkshopReceiver()
instructor_confirmed_for_workshop_signal.connect(instructor_confirmed_for_workshop_receiver)
instructor_confirmed_for_workshop_update_receiver = InstructorConfirmedForWorkshopUpdateReceiver()
instructor_confirmed_for_workshop_update_signal.connect(instructor_confirmed_for_workshop_update_receiver)
instructor_confirmed_for_workshop_cancel_receiver = InstructorConfirmedForWorkshopCancelReceiver()
instructor_confirmed_for_workshop_cancel_signal.connect(instructor_confirmed_for_workshop_cancel_receiver)
