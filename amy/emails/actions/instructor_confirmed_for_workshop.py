from datetime import datetime
import logging
from typing import Any

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
    scalar_value_url,
)
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Event, Person, TagQuerySet, Task

logger = logging.getLogger("amy")


def instructor_confirmed_for_workshop_strategy(
    task: Task, optional_task_pk: int | None = None
) -> StrategyEnum:
    logger.info(f"Running InstructorConfirmedForWorkshop strategy for {task=}")

    instructor_role = task.role.name == "instructor"
    person_email_exists = bool(task.person.email)
    carpentries_tags = task.event.tags.filter(
        name__in=TagQuerySet.CARPENTRIES_TAG_NAMES
    ).exclude(name__in=TagQuerySet.NON_CARPENTRIES_TAG_NAMES)
    centrally_organised = (
        task.event.administrator and task.event.administrator.domain != "self-organized"
    )

    log_condition_elements(
        task=task,
        task_pk=task.pk,
        optional_task_pk=optional_task_pk,
        instructor_role=instructor_role,
        person_email_exists=person_email_exists,
        carpentries_tags=carpentries_tags,
        centrally_organised=centrally_organised,
    )

    email_should_exist = (
        task.pk
        and instructor_role
        and person_email_exists
        and carpentries_tags
        and centrally_organised
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(Task)  # type: ignore
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=optional_task_pk or task.pk,
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
    task = Task.objects.filter(pk=kwargs["task_id"]).first()
    instructor_recruitment_signup = InstructorRecruitmentSignup.objects.filter(
        pk=kwargs["instructor_recruitment_signup_id"]
    ).first()
    return {
        "person": person,
        "event": event,
        "task": task,
        "task_id": kwargs["task_id"],
        "instructor_recruitment_signup": instructor_recruitment_signup,
    }


def get_context_json(context: InstructorConfirmedContext) -> ContextModel:
    signup = context["instructor_recruitment_signup"]
    task = context["task"]
    return ContextModel(
        {
            "person": api_model_url("person", context["person"].pk),
            "event": api_model_url("event", context["event"].pk),
            "task": api_model_url("task", task.pk) if task else scalar_value_none(),
            "task_id": scalar_value_url("int", f"{context['task_id']}"),
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
) -> Task:
    # When removing task, this will be None.
    return context["task"]  # type: ignore


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
    ) -> Task:
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
    ) -> Task:
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

    def get_generic_relation_content_type(
        self, context: InstructorConfirmedContext, generic_relation_obj: Any
    ) -> ContentType:
        return ContentType.objects.get_for_model(Task)

    def get_generic_relation_pk(
        self, context: InstructorConfirmedContext, generic_relation_obj: Any
    ) -> int | Any:
        return context["task_id"]

    def get_generic_relation_object(
        self,
        context: InstructorConfirmedContext,
        **kwargs: Unpack[InstructorConfirmedKwargs],
    ) -> Task:
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
