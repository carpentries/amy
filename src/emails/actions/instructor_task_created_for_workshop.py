import logging
from datetime import datetime
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from src.emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from src.emails.actions.base_strategy import run_strategy
from src.emails.models import ScheduledEmail
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME,
    Signal,
    instructor_task_created_for_workshop_cancel_signal,
    instructor_task_created_for_workshop_signal,
    instructor_task_created_for_workshop_update_signal,
)
from src.emails.types import (
    InstructorTaskCreatedForWorkshopContext,
    InstructorTaskCreatedForWorkshopKwargs,
    StrategyEnum,
)
from src.emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    scalar_value_none,
    scalar_value_url,
)
from src.workshops.models import Event, Person, TagQuerySet, Task

logger = logging.getLogger("amy")


def instructor_task_created_for_workshop_strategy(task: Task, optional_task_pk: int | None = None) -> StrategyEnum:
    logger.info(f"Running InstructorTaskCreatedForWorkshopForWorkshop strategy for {task=}")

    instructor_role = task.role.name == "instructor"
    person_email_exists = bool(task.person.email)
    carpentries_tags = task.event.tags.filter(name__in=TagQuerySet.CARPENTRIES_TAG_NAMES).exclude(
        name__in=TagQuerySet.NON_CARPENTRIES_TAG_NAMES
    )
    centrally_organised = task.event.administrator and task.event.administrator.domain != "self-organized"
    start_date_in_future = task.event.start and task.event.start >= timezone.now().date()

    log_condition_elements(
        task=task,
        task_pk=task.pk,
        optional_task_pk=optional_task_pk,
        instructor_role=instructor_role,
        person_email_exists=person_email_exists,
        carpentries_tags=carpentries_tags,
        centrally_organised=centrally_organised,
        start_date_in_future=start_date_in_future,
    )

    email_should_exist = (
        task.pk
        and instructor_role
        and person_email_exists
        and carpentries_tags
        and centrally_organised
        and start_date_in_future
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(Task)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=optional_task_pk or task.pk,
        template__signal=INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME,
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

    logger.debug(f"InstructorTaskCreatedForWorkshop strategy {result=}")
    return result


def run_instructor_task_created_for_workshop_strategy(
    strategy: StrategyEnum, request: HttpRequest, task: Task, **kwargs: Any
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_task_created_for_workshop_signal,
        StrategyEnum.UPDATE: instructor_task_created_for_workshop_update_signal,
        StrategyEnum.CANCEL: instructor_task_created_for_workshop_cancel_signal,
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


def get_scheduled_at(
    **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
) -> InstructorTaskCreatedForWorkshopContext:
    person = Person.objects.get(pk=kwargs["person_id"])
    event = Event.objects.get(pk=kwargs["event_id"])
    task = Task.objects.filter(pk=kwargs["task_id"]).first()
    return {
        "person": person,
        "event": event,
        "task": task,
        "task_id": kwargs["task_id"],
    }


def get_context_json(context: InstructorTaskCreatedForWorkshopContext) -> ContextModel:
    task = context["task"]
    return ContextModel(
        {
            "person": api_model_url("person", context["person"].pk),
            "event": api_model_url("event", context["event"].pk),
            "task": api_model_url("task", task.pk) if task else scalar_value_none(),
            "task_id": scalar_value_url("int", f"{context['task_id']}"),
        },
    )


def get_generic_relation_object(
    context: InstructorTaskCreatedForWorkshopContext,
    **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
) -> Task:
    # When removing task, this will be None.
    return context["task"]  # type: ignore


def get_recipients(
    context: InstructorTaskCreatedForWorkshopContext,
    **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
) -> list[str]:
    person = context["person"]
    return [person.email] if person.email else []


def get_recipients_context_json(
    context: InstructorTaskCreatedForWorkshopContext,
    **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", context["person"].pk),
                property="email",
            )
        ],
    )


class InstructorTaskCreatedForWorkshopReceiver(BaseAction):
    signal = instructor_task_created_for_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs]
    ) -> InstructorTaskCreatedForWorkshopContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTaskCreatedForWorkshopContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> Task:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorTaskCreatedForWorkshopUpdateReceiver(BaseActionUpdate):
    signal = instructor_task_created_for_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs]
    ) -> InstructorTaskCreatedForWorkshopContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTaskCreatedForWorkshopContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> Task:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorTaskCreatedForWorkshopCancelReceiver(BaseActionCancel):
    signal = instructor_task_created_for_workshop_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs]
    ) -> InstructorTaskCreatedForWorkshopContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTaskCreatedForWorkshopContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_content_type(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        generic_relation_obj: Any,
    ) -> ContentType:
        return ContentType.objects.get_for_model(Task)

    def get_generic_relation_pk(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        generic_relation_obj: Any,
    ) -> int | Any:
        return context["task_id"]

    def get_generic_relation_object(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> Task:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTaskCreatedForWorkshopContext,
        **kwargs: Unpack[InstructorTaskCreatedForWorkshopKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


instructor_task_created_for_workshop_receiver = InstructorTaskCreatedForWorkshopReceiver()
instructor_task_created_for_workshop_signal.connect(instructor_task_created_for_workshop_receiver)
instructor_task_created_for_workshop_update_receiver = InstructorTaskCreatedForWorkshopUpdateReceiver()
instructor_task_created_for_workshop_update_signal.connect(instructor_task_created_for_workshop_update_receiver)
instructor_task_created_for_workshop_cancel_receiver = InstructorTaskCreatedForWorkshopCancelReceiver()
instructor_task_created_for_workshop_cancel_signal.connect(instructor_task_created_for_workshop_cancel_receiver)
