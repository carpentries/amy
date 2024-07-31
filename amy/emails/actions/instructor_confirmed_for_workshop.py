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
from emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    scalar_value_none,
)
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Event, Person, Task

logger = logging.getLogger("amy")


def instructor_confirmed_for_workshop_strategy(task: Task) -> StrategyEnum:
    logger.info(f"Running InstructorConfirmedForWorkshop strategy for {task=}")

    instructor_role = task.role.name == "instructor"
    person_email_exists = bool(task.person.email)

    log_condition_elements(
        instructor_role=instructor_role,
        person_email_exists=person_email_exists,
    )

    email_should_exist = instructor_role and person_email_exists
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(task.person)  # type: ignore
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=task.person.pk,
        template__signal=INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
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

    logger.debug(f"InstructorConfirmedForWorkshop strategy {result = }")
    return result


def run_instructor_confirmed_for_workshop_strategy(
    strategy: StrategyEnum, request: HttpRequest, task: Task, **kwargs
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
        sender=task,
        task=task,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[InstructorConfirmedKwargs]) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[InstructorConfirmedKwargs],
) -> InstructorConfirmedContext:
    person = Person.objects.get(pk=kwargs["person_id"])
    event = Event.objects.get(pk=kwargs["event_id"])
    instructor_recruitment_signup = InstructorRecruitmentSignup.objects.filter(
        pk=kwargs["instructor_recruitment_signup_id"]
    ).first()
    return {
        "person": person,
        "event": event,
        "instructor_recruitment_signup": instructor_recruitment_signup,
    }


def get_context_json(context: InstructorConfirmedContext) -> ContextModel:
    signup = context["instructor_recruitment_signup"]
    return ContextModel(
        {
            "person": api_model_url("person", context["person"].pk),
            "event": api_model_url("event", context["event"].pk),
            "instructor_recruitment_signup": (
                api_model_url(
                    "instructorrecruitmentsignup",
                    signup.pk,
                )
                if signup
                else scalar_value_none()
            ),
        },
    )


def get_generic_relation_object(
    context: InstructorConfirmedContext, **kwargs: Unpack[InstructorConfirmedKwargs]
) -> Person:
    return context["person"]


def get_recipients(
    context: InstructorConfirmedContext, **kwargs: Unpack[InstructorConfirmedKwargs]
) -> list[str]:
    person = context["person"]
    return [person.email] if person.email else []


def get_recipients_context_json(
    context: InstructorConfirmedContext,
    **kwargs: Unpack[InstructorConfirmedKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            {
                "api_uri": api_model_url("person", context["person"].pk),
                "property": "email",
            },  # type: ignore
        ],
    )


class InstructorConfirmedForWorkshopReceiver(BaseAction):
    signal = instructor_confirmed_for_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorConfirmedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorConfirmedKwargs]
    ) -> InstructorConfirmedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorConfirmedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> Person:
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

    def get_context(
        self, **kwargs: Unpack[InstructorConfirmedKwargs]
    ) -> InstructorConfirmedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorConfirmedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> Person:
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

    def get_context(
        self, **kwargs: Unpack[InstructorConfirmedKwargs]
    ) -> InstructorConfirmedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorConfirmedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> Person:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


instructor_confirmed_for_workshop_receiver = InstructorConfirmedForWorkshopReceiver()
instructor_confirmed_for_workshop_signal.connect(
    instructor_confirmed_for_workshop_receiver
)
instructor_confirmed_for_workshop_update_receiver = (
    InstructorConfirmedForWorkshopUpdateReceiver()
)
instructor_confirmed_for_workshop_update_signal.connect(
    instructor_confirmed_for_workshop_update_receiver
)
instructor_confirmed_for_workshop_cancel_receiver = (
    InstructorConfirmedForWorkshopCancelReceiver()
)
instructor_confirmed_for_workshop_cancel_signal.connect(
    instructor_confirmed_for_workshop_cancel_receiver
)
