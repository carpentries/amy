from datetime import datetime
import logging

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from typing_extensions import Unpack

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.models import ScheduledEmail, ScheduledEmailStatus
from emails.signals import (
    NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
    Signal,
    new_membership_onboarding_remove_signal,
    new_membership_onboarding_signal,
    new_membership_onboarding_update_signal,
)
from emails.types import (
    NewMembershipOnboardingContext,
    NewMembershipOnboardingKwargs,
    StrategyEnum,
)
from emails.utils import immediate_action, one_month_before
from fiscal.models import MembershipTask
from workshops.models import Membership

from .instructor_training_approaching import EmailStrategyException

logger = logging.getLogger("amy")

MEMBERSHIP_TASK_ROLES_EXPECTED = ["billing_contact", "programmatic_contact"]


def new_membership_onboarding_strategy(membership: Membership) -> StrategyEnum:
    logger.info(f"Running NewMembershipOnboarding strategy for {membership}")

    ct = ContentType.objects.get_for_model(membership)  # type: ignore
    email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=membership.pk,
        template__signal=NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
        state=ScheduledEmailStatus.SCHEDULED,
    ).exists()

    # Membership can't be removed without removing the tasks first. This is when the
    # email would be de-scheduled.
    email_should_exist = (
        membership.pk
        and getattr(membership, "rolled_from_membership", None) is None
        and MembershipTask.objects.filter(
            membership=membership, role__name__in=MEMBERSHIP_TASK_ROLES_EXPECTED
        ).count()
    )

    if not email_scheduled and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_scheduled and not email_should_exist:
        result = StrategyEnum.REMOVE
    elif email_scheduled and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"NewMembershipOnboarding strategy {result = }")
    return result


# TODO: turn into a generic function/class
def run_new_membership_onboarding_strategy(
    strategy: StrategyEnum, request: HttpRequest, membership: Membership
) -> None:
    mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: new_membership_onboarding_signal,
        StrategyEnum.UPDATE: new_membership_onboarding_update_signal,
        StrategyEnum.REMOVE: new_membership_onboarding_remove_signal,
        StrategyEnum.NOOP: None,
    }
    if strategy not in mapping:
        raise EmailStrategyException(f"Unknown strategy {strategy}")

    signal = mapping[strategy]

    if not signal:
        logger.debug(f"Strategy {strategy} for {membership} is a no-op")
        return

    logger.debug(f"Sending signal for {membership} as result of strategy {strategy}")

    signal.send(
        sender=membership,
        request=request,
        membership=membership,
    )


def get_scheduled_at(**kwargs: Unpack[NewMembershipOnboardingKwargs]) -> datetime:
    return max(
        one_month_before(kwargs["membership"].agreement_start), immediate_action()
    )


def get_context(
    **kwargs: Unpack[NewMembershipOnboardingKwargs],
) -> NewMembershipOnboardingContext:
    membership = kwargs["membership"]

    return {
        "membership": membership,
    }


def get_generic_relation_object(
    context: NewMembershipOnboardingContext,
    **kwargs: Unpack[NewMembershipOnboardingKwargs],
) -> Membership:
    return context["membership"]


def get_recipients(
    context: NewMembershipOnboardingContext,
    **kwargs: Unpack[NewMembershipOnboardingKwargs],
) -> list[str]:
    membership = context["membership"]
    tasks = MembershipTask.objects.filter(
        membership=membership,
        role__name__in=MEMBERSHIP_TASK_ROLES_EXPECTED,
    ).select_related("person", "role")
    return [task.person.email for task in tasks if task.person.email]


class NewMembershipOnboardingReceiver(BaseAction):
    signal = new_membership_onboarding_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[NewMembershipOnboardingKwargs]
    ) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[NewMembershipOnboardingKwargs]
    ) -> NewMembershipOnboardingContext:
        return get_context(**kwargs)

    def get_generic_relation_object(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)


class NewMembershipOnboardingUpdateReceiver(BaseActionUpdate):
    signal = new_membership_onboarding_update_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[NewMembershipOnboardingKwargs]
    ) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[NewMembershipOnboardingKwargs]
    ) -> NewMembershipOnboardingContext:
        return get_context(**kwargs)

    def get_generic_relation_object(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)


class NewMembershipOnboardingCancelReceiver(BaseActionCancel):
    signal = new_membership_onboarding_remove_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[NewMembershipOnboardingKwargs]
    ) -> NewMembershipOnboardingContext:
        return get_context(**kwargs)

    def get_generic_relation_object(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

new_membership_onboarding_receiver = NewMembershipOnboardingReceiver()
new_membership_onboarding_signal.connect(new_membership_onboarding_receiver)


new_membership_onboarding_update_receiver = NewMembershipOnboardingUpdateReceiver()
new_membership_onboarding_update_signal.connect(
    new_membership_onboarding_update_receiver
)


new_membership_onboarding_remove_receiver = NewMembershipOnboardingCancelReceiver()
new_membership_onboarding_remove_signal.connect(
    new_membership_onboarding_remove_receiver
)
