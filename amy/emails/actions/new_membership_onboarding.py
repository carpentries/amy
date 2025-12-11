from datetime import datetime
import logging
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.models import ScheduledEmail
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
    Signal,
    new_membership_onboarding_cancel_signal,
    new_membership_onboarding_signal,
    new_membership_onboarding_update_signal,
)
from emails.types import (
    NewMembershipOnboardingContext,
    NewMembershipOnboardingKwargs,
    StrategyEnum,
)
from emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    one_month_before,
)
from fiscal.models import MembershipTask
from workshops.models import Membership

logger = logging.getLogger("amy")

MEMBERSHIP_TASK_ROLES_EXPECTED = ["billing_contact", "programmatic_contact"]
MEMBERSHIP_ACCEPTABLE_VARIANTS = ["bronze", "silver", "gold", "platinum", "titanium"]


def new_membership_onboarding_strategy(membership: Membership) -> StrategyEnum:
    logger.info(f"Running NewMembershipOnboarding strategy for {membership}")

    ct = ContentType.objects.get_for_model(membership)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=membership.pk,
        template__signal=NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
    ).exists()
    task_count = MembershipTask.objects.filter(
        membership_id=membership.pk, role__name__in=MEMBERSHIP_TASK_ROLES_EXPECTED
    ).count()
    membership_acceptable_variant = membership.variant in MEMBERSHIP_ACCEPTABLE_VARIANTS
    titanium_variant = membership.variant == "titanium"
    condition_for_titanium = (
        not titanium_variant
        or titanium_variant
        and any(
            [
                membership.workshops_without_admin_fee_per_agreement,
                membership.public_instructor_training_seats,
                membership.additional_public_instructor_training_seats,
                membership.inhouse_instructor_training_seats,
                membership.additional_inhouse_instructor_training_seats,
            ]
        )
    )

    log_condition_elements(
        **{
            "membership.pk": membership.pk,
            "task_count": task_count,
            "membership.variant": membership.variant,
            "membership_acceptable_variant": membership_acceptable_variant,
            "titanium_variant": titanium_variant,
            "condition_for_titanium": condition_for_titanium,
        }
    )

    # Membership can't be removed without removing the tasks first. This is when the
    # email would be de-scheduled.
    # UPDATE 2025-02-15 (#2761):
    #      We're allowing scheduling only for bronze, silver, gold or platinum variants.
    email_should_exist = bool(membership.pk and task_count and membership_acceptable_variant and condition_for_titanium)

    if not email_exists and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_exists and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif email_exists and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"NewMembershipOnboarding strategy {result=}")
    return result


def run_new_membership_onboarding_strategy(
    strategy: StrategyEnum, request: HttpRequest, membership: Membership, **kwargs: Any
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: new_membership_onboarding_signal,
        StrategyEnum.UPDATE: new_membership_onboarding_update_signal,
        StrategyEnum.CANCEL: new_membership_onboarding_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=membership,
        membership=membership,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[NewMembershipOnboardingKwargs]) -> datetime:
    return max(one_month_before(kwargs["membership"].agreement_start), immediate_action())


def get_context(
    **kwargs: Unpack[NewMembershipOnboardingKwargs],
) -> NewMembershipOnboardingContext:
    membership = kwargs["membership"]

    return {
        "membership": membership,
    }


def get_context_json(context: NewMembershipOnboardingContext) -> ContextModel:
    return ContextModel(
        {
            "membership": api_model_url("membership", context["membership"].pk),
        },
    )


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


def get_recipients_context_json(
    context: NewMembershipOnboardingContext,
    **kwargs: Unpack[NewMembershipOnboardingKwargs],
) -> ToHeaderModel:
    membership = context["membership"]
    tasks = MembershipTask.objects.filter(
        membership=membership,
        role__name__in=MEMBERSHIP_TASK_ROLES_EXPECTED,
    ).select_related("person")

    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", task.person.pk),
                property="email",
            )
            for task in tasks
        ],
    )


class NewMembershipOnboardingReceiver(BaseAction):
    signal = new_membership_onboarding_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[NewMembershipOnboardingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[NewMembershipOnboardingKwargs]) -> NewMembershipOnboardingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: NewMembershipOnboardingContext) -> ContextModel:
        return get_context_json(context)

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

    def get_recipients_context_json(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class NewMembershipOnboardingUpdateReceiver(BaseActionUpdate):
    signal = new_membership_onboarding_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[NewMembershipOnboardingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[NewMembershipOnboardingKwargs]) -> NewMembershipOnboardingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: NewMembershipOnboardingContext) -> ContextModel:
        return get_context_json(context)

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

    def get_recipients_context_json(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class NewMembershipOnboardingCancelReceiver(BaseActionCancel):
    signal = new_membership_onboarding_cancel_signal.signal_name

    def get_context(self, **kwargs: Unpack[NewMembershipOnboardingKwargs]) -> NewMembershipOnboardingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: NewMembershipOnboardingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> Membership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: NewMembershipOnboardingContext,
        **kwargs: Unpack[NewMembershipOnboardingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

new_membership_onboarding_receiver = NewMembershipOnboardingReceiver()
new_membership_onboarding_signal.connect(new_membership_onboarding_receiver)


new_membership_onboarding_update_receiver = NewMembershipOnboardingUpdateReceiver()
new_membership_onboarding_update_signal.connect(new_membership_onboarding_update_receiver)


new_membership_onboarding_cancel_receiver = NewMembershipOnboardingCancelReceiver()
new_membership_onboarding_cancel_signal.connect(new_membership_onboarding_cancel_receiver)
