from datetime import datetime, timedelta
import logging
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.models import ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
    Signal,
    membership_quarterly_3_months_cancel_signal,
    membership_quarterly_3_months_signal,
    membership_quarterly_3_months_update_signal,
    membership_quarterly_6_months_cancel_signal,
    membership_quarterly_6_months_signal,
    membership_quarterly_6_months_update_signal,
    membership_quarterly_9_months_cancel_signal,
    membership_quarterly_9_months_signal,
    membership_quarterly_9_months_update_signal,
)
from emails.types import (
    MembershipQuarterlyContext,
    MembershipQuarterlyKwargs,
    StrategyEnum,
)
from emails.utils import (
    api_model_url,
    log_condition_elements,
    shift_date_and_apply_current_utc_time,
)
from fiscal.models import MembershipTask
from workshops.models import Membership

logger = logging.getLogger("amy")

MEMBERSHIP_ACCEPTABLE_VARIANTS = ["bronze", "silver", "gold", "platinum"]
SCHEDULED_AT_MAPPING = {
    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME: ("agreement_start", timedelta(days=30 * 3)),
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME: ("agreement_start", timedelta(days=30 * 6)),
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME: ("agreement_end", -timedelta(days=30 * 3)),
}


def membership_quarterly_email_strategy(signal_name: str, membership: Membership) -> StrategyEnum:
    logger.info(f"Running MembershipQuarterlyEmail ({signal_name}) strategy for {membership}")

    ct = ContentType.objects.get_for_model(membership)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=membership.pk,
        template__signal=signal_name,
    ).exists()
    task_count = MembershipTask.objects.filter(membership_id=membership.pk).count()
    membership_acceptable_variant = membership.variant in MEMBERSHIP_ACCEPTABLE_VARIANTS

    log_condition_elements(
        **{
            "membership.pk": membership.pk,
            "task_count": task_count,
            "membership.variant": membership.variant,
            "membership_acceptable_variant": membership_acceptable_variant,
        }
    )

    email_should_exist = bool(membership.pk and task_count and membership_acceptable_variant)

    if not email_exists and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_exists and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif email_exists and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"MembershipQuarterlyEmail ({signal_name}) strategy {result=}")
    return result


def run_membership_quarterly_email_strategy(
    signal_name: str, strategy: StrategyEnum, request: HttpRequest, membership: Membership, **kwargs: Any
) -> None:
    signal_mapping: dict[str, dict[StrategyEnum, Signal | None]] = {
        MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME: {
            StrategyEnum.CREATE: membership_quarterly_3_months_signal,
            StrategyEnum.UPDATE: membership_quarterly_3_months_update_signal,
            StrategyEnum.CANCEL: membership_quarterly_3_months_cancel_signal,
            StrategyEnum.NOOP: None,
        },
        MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME: {
            StrategyEnum.CREATE: membership_quarterly_6_months_signal,
            StrategyEnum.UPDATE: membership_quarterly_6_months_update_signal,
            StrategyEnum.CANCEL: membership_quarterly_6_months_cancel_signal,
            StrategyEnum.NOOP: None,
        },
        MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME: {
            StrategyEnum.CREATE: membership_quarterly_9_months_signal,
            StrategyEnum.UPDATE: membership_quarterly_9_months_update_signal,
            StrategyEnum.CANCEL: membership_quarterly_9_months_cancel_signal,
            StrategyEnum.NOOP: None,
        },
    }
    selected_signal_mapping = signal_mapping[signal_name]

    return run_strategy(
        strategy,
        selected_signal_mapping,
        request,
        sender=membership,
        membership=membership,
        **kwargs,
    )


def get_scheduled_at(signal_name: str, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> datetime:
    attribute, offset = SCHEDULED_AT_MAPPING[signal_name]
    return shift_date_and_apply_current_utc_time(
        getattr(kwargs["membership"], attribute),
        offset=offset,
    )


def get_context(**kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
    membership = kwargs["membership"]
    contacts = [
        task.person
        for task in MembershipTask.objects.filter(
            membership=membership,
        ).select_related("person")
    ]
    events = list(membership.event_set.all())
    tasks = list(membership.task_set.select_related("person").all())
    persons = [task.person for task in membership.task_set.all()]

    return {
        "membership": membership,
        "member_contacts": contacts,
        "events": events,
        "trainee_tasks": tasks,
        "trainees": persons,
    }


def get_context_json(context: MembershipQuarterlyContext) -> ContextModel:
    return ContextModel(
        {
            "membership": api_model_url("membership", context["membership"].pk),
            "member_contacts": [api_model_url("person", person.pk) for person in context["member_contacts"]],
            "events": [api_model_url("event", event.pk) for event in context["events"]],
            "trainee_tasks": [api_model_url("task", task.pk) for task in context["trainee_tasks"]],
            "trainees": [api_model_url("person", person.pk) for person in context["trainees"]],
        },
    )


def get_generic_relation_object(
    context: MembershipQuarterlyContext,
    **kwargs: Unpack[MembershipQuarterlyKwargs],
) -> Membership:
    return context["membership"]


def get_recipients(
    context: MembershipQuarterlyContext,
    **kwargs: Unpack[MembershipQuarterlyKwargs],
) -> list[str]:
    membership = context["membership"]
    tasks = MembershipTask.objects.filter(membership=membership).select_related("person")
    return [task.person.email for task in tasks if task.person.email]


def get_recipients_context_json(
    context: MembershipQuarterlyContext,
    **kwargs: Unpack[MembershipQuarterlyKwargs],
) -> ToHeaderModel:
    membership = context["membership"]
    tasks = MembershipTask.objects.filter(membership=membership).select_related("person")

    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", task.person.pk),
                property="email",
            )
            for task in tasks
            if task.person.email
        ],
    )


def update_context_json_and_to_header_json(
    signal_name: str,
    request: HttpRequest,
    membership: Membership,
) -> ScheduledEmail | None:
    ct = ContentType.objects.get_for_model(membership)
    email = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=membership.pk,
        template__signal=signal_name,
        state=ScheduledEmailStatus.SCHEDULED,
    ).first()
    if not email:
        return None

    context = get_context(membership=membership)
    context_json = get_context_json(context)
    to_header = get_recipients(context, membership=membership)
    to_header_context_json = get_recipients_context_json(context, membership=membership)
    email.context_json = context_json.model_dump()
    email.to_header = to_header
    email.to_header_context_json = to_header_context_json.model_dump()
    email.save()
    return email


# -----------------------------------------------------------------------------
# 3 months after start


class MembershipQuarterly3MonthsReceiver(BaseAction):
    signal = membership_quarterly_3_months_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> datetime:
        return get_scheduled_at(self.signal, **kwargs)

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class MembershipQuarterly3MonthsUpdateReceiver(BaseActionUpdate):
    signal = membership_quarterly_3_months_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> datetime:
        return get_scheduled_at(self.signal, **kwargs)

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class MembershipQuarterly3MonthsCancelReceiver(BaseActionCancel):
    signal = membership_quarterly_3_months_cancel_signal.signal_name

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# 6 months after start


class MembershipQuarterly6MonthsReceiver(BaseAction):
    signal = membership_quarterly_6_months_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> datetime:
        return get_scheduled_at(self.signal, **kwargs)

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class MembershipQuarterly6MonthsUpdateReceiver(BaseActionUpdate):
    signal = membership_quarterly_6_months_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> datetime:
        return get_scheduled_at(self.signal, **kwargs)

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class MembershipQuarterly6MonthsCancelReceiver(BaseActionCancel):
    signal = membership_quarterly_6_months_cancel_signal.signal_name

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# 3 months before end


class MembershipQuarterly9MonthsReceiver(BaseAction):
    signal = membership_quarterly_9_months_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> datetime:
        return get_scheduled_at(self.signal, **kwargs)

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class MembershipQuarterly9MonthsUpdateReceiver(BaseActionUpdate):
    signal = membership_quarterly_9_months_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> datetime:
        return get_scheduled_at(self.signal, **kwargs)

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class MembershipQuarterly9MonthsCancelReceiver(BaseActionCancel):
    signal = membership_quarterly_9_months_cancel_signal.signal_name

    def get_context(self, **kwargs: Unpack[MembershipQuarterlyKwargs]) -> MembershipQuarterlyContext:
        return get_context(**kwargs)

    def get_context_json(self, context: MembershipQuarterlyContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: MembershipQuarterlyContext,
        **kwargs: Unpack[MembershipQuarterlyKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

membership_quarterly_3_months_receiver = MembershipQuarterly3MonthsReceiver()
membership_quarterly_3_months_signal.connect(membership_quarterly_3_months_receiver)
membership_quarterly_3_months_update_receiver = MembershipQuarterly3MonthsUpdateReceiver()
membership_quarterly_3_months_update_signal.connect(membership_quarterly_3_months_update_receiver)
membership_quarterly_3_months_cancel_receiver = MembershipQuarterly3MonthsCancelReceiver()
membership_quarterly_3_months_cancel_signal.connect(membership_quarterly_3_months_cancel_receiver)

membership_quarterly_6_months_receiver = MembershipQuarterly6MonthsReceiver()
membership_quarterly_6_months_signal.connect(membership_quarterly_6_months_receiver)
membership_quarterly_6_months_update_receiver = MembershipQuarterly6MonthsUpdateReceiver()
membership_quarterly_6_months_update_signal.connect(membership_quarterly_6_months_update_receiver)
membership_quarterly_6_months_cancel_receiver = MembershipQuarterly6MonthsCancelReceiver()
membership_quarterly_6_months_cancel_signal.connect(membership_quarterly_6_months_cancel_receiver)

membership_quarterly_9_months_receiver = MembershipQuarterly9MonthsReceiver()
membership_quarterly_9_months_signal.connect(membership_quarterly_9_months_receiver)
membership_quarterly_9_months_update_receiver = MembershipQuarterly9MonthsUpdateReceiver()
membership_quarterly_9_months_update_signal.connect(membership_quarterly_9_months_update_receiver)
membership_quarterly_9_months_cancel_receiver = MembershipQuarterly9MonthsCancelReceiver()
membership_quarterly_9_months_cancel_signal.connect(membership_quarterly_9_months_cancel_receiver)
