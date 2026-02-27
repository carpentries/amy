import logging
from datetime import datetime
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from src.emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from src.emails.actions.base_strategy import run_strategy
from src.emails.models import ScheduledEmail
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME,
    Signal,
    new_partnership_onboarding_cancel_signal,
    new_partnership_onboarding_signal,
    new_partnership_onboarding_update_signal,
)
from src.emails.types import (
    NewPartnershipOnboardingContext,
    NewPartnershipOnboardingKwargs,
    StrategyEnum,
)
from src.emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    one_month_before,
)
from src.fiscal.models import Partnership
from src.offering.models import AccountOwner

logger = logging.getLogger("amy")


ACCOUNT_OWNER_PERMISSION_TYPES_EXPECTED = ["owner", "programmatic_contact"]


def new_partnership_onboarding_strategy(partnership: Partnership) -> StrategyEnum:
    logger.info(f"Running NewPartnershipOnboarding strategy for {partnership}")

    ct = ContentType.objects.get_for_model(partnership)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=partnership.pk,
        template__signal=NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME,
    ).exists()
    account_owners_exist = AccountOwner.objects.filter(
        account_id=partnership.account_id, permission_type__in=ACCOUNT_OWNER_PERMISSION_TYPES_EXPECTED
    ).exists()

    log_condition_elements(
        **{
            "partnership.pk": partnership.pk,
            "account_owners_exist": account_owners_exist,
        }
    )

    email_should_exist = bool(partnership.pk and account_owners_exist)

    if not email_exists and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_exists and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif email_exists and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"NewPartnershipOnboarding strategy {result=}")
    return result


def run_new_partnership_onboarding_strategy(
    strategy: StrategyEnum, request: HttpRequest, partnership: Partnership, **kwargs: Any
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: new_partnership_onboarding_signal,
        StrategyEnum.UPDATE: new_partnership_onboarding_update_signal,
        StrategyEnum.CANCEL: new_partnership_onboarding_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=partnership,
        partnership=partnership,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[NewPartnershipOnboardingKwargs]) -> datetime:
    return max(one_month_before(kwargs["partnership"].agreement_start), immediate_action())


def get_context(
    **kwargs: Unpack[NewPartnershipOnboardingKwargs],
) -> NewPartnershipOnboardingContext:
    partnership = kwargs["partnership"]

    return {
        "partnership": partnership,
    }


def get_context_json(context: NewPartnershipOnboardingContext) -> ContextModel:
    return ContextModel(
        {
            "partnership": api_model_url("partnership", context["partnership"].pk),
        },
    )


def get_generic_relation_object(
    context: NewPartnershipOnboardingContext,
    **kwargs: Unpack[NewPartnershipOnboardingKwargs],
) -> Partnership:
    return context["partnership"]


def get_recipients(
    context: NewPartnershipOnboardingContext,
    **kwargs: Unpack[NewPartnershipOnboardingKwargs],
) -> list[str]:
    partnership = context["partnership"]
    owners = AccountOwner.objects.filter(
        account_id=partnership.account_id, permission_type__in=ACCOUNT_OWNER_PERMISSION_TYPES_EXPECTED
    ).select_related("person")
    return [owner.person.email for owner in owners if owner.person.email]


def get_recipients_context_json(
    context: NewPartnershipOnboardingContext,
    **kwargs: Unpack[NewPartnershipOnboardingKwargs],
) -> ToHeaderModel:
    partnership = context["partnership"]
    owners = AccountOwner.objects.filter(
        account_id=partnership.account_id, permission_type__in=ACCOUNT_OWNER_PERMISSION_TYPES_EXPECTED
    ).select_related("person")

    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", owner.person.pk),
                property="email",
            )
            for owner in owners
        ],
    )


class NewPartnershipOnboardingReceiver(BaseAction):
    signal = new_partnership_onboarding_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[NewPartnershipOnboardingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[NewPartnershipOnboardingKwargs]) -> NewPartnershipOnboardingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: NewPartnershipOnboardingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> Partnership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class NewPartnershipOnboardingUpdateReceiver(BaseActionUpdate):
    signal = new_partnership_onboarding_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[NewPartnershipOnboardingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[NewPartnershipOnboardingKwargs]) -> NewPartnershipOnboardingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: NewPartnershipOnboardingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> Partnership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class NewPartnershipOnboardingCancelReceiver(BaseActionCancel):
    signal = new_partnership_onboarding_cancel_signal.signal_name

    def get_context(self, **kwargs: Unpack[NewPartnershipOnboardingKwargs]) -> NewPartnershipOnboardingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: NewPartnershipOnboardingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> Partnership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: NewPartnershipOnboardingContext,
        **kwargs: Unpack[NewPartnershipOnboardingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

new_partnership_onboarding_receiver = NewPartnershipOnboardingReceiver()
new_partnership_onboarding_signal.connect(new_partnership_onboarding_receiver)


new_partnership_onboarding_update_receiver = NewPartnershipOnboardingUpdateReceiver()
new_partnership_onboarding_update_signal.connect(new_partnership_onboarding_update_receiver)


new_partnership_onboarding_cancel_receiver = NewPartnershipOnboardingCancelReceiver()
new_partnership_onboarding_cancel_signal.connect(new_partnership_onboarding_cancel_receiver)
