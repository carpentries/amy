import logging
from datetime import datetime, timedelta
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from src.emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from src.emails.actions.base_strategy import run_strategy
from src.emails.models import ScheduledEmail
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    PARTNERSHIP_AGREEMENT_ENDING_SIGNAL_NAME,
    Signal,
    partnership_agreement_ending_cancel_signal,
    partnership_agreement_ending_signal,
    partnership_agreement_ending_update_signal,
)
from src.emails.types import (
    PartnershipAgreementEndingContext,
    PartnershipAgreementEndingKwargs,
    StrategyEnum,
)
from src.emails.utils import (
    api_model_url,
    log_condition_elements,
    shift_date_and_apply_current_utc_time,
)
from src.fiscal.models import Partnership
from src.offering.models import AccountOwner

logger = logging.getLogger("amy")


ACCOUNT_OWNER_PERMISSION_TYPES_EXPECTED = ["owner", "programmatic_contact"]
AGREEMENT_ENDING_OFFSET = -timedelta(days=90)


def partnership_agreement_ending_strategy(partnership: Partnership) -> StrategyEnum:
    logger.info(f"Running PartnershipAgreementEnding strategy for {partnership}")

    ct = ContentType.objects.get_for_model(partnership)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=partnership.pk,
        template__signal=PARTNERSHIP_AGREEMENT_ENDING_SIGNAL_NAME,
    ).exists()
    account_owners_exist = AccountOwner.objects.filter(
        account_id=partnership.account_id, permission_type__in=ACCOUNT_OWNER_PERMISSION_TYPES_EXPECTED
    ).exists()

    email_scheduled_date_in_future = bool(
        partnership.pk
        and shift_date_and_apply_current_utc_time(partnership.agreement_end, offset=AGREEMENT_ENDING_OFFSET)
        >= timezone.now()
    )

    log_condition_elements(
        **{
            "partnership.pk": partnership.pk,
            "account_owners_exist": account_owners_exist,
            "email_scheduled_date_in_future": email_scheduled_date_in_future,
        }
    )

    email_should_exist = bool(partnership.pk and account_owners_exist and email_scheduled_date_in_future)

    if not email_exists and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_exists and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif email_exists and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"PartnershipAgreementEnding strategy {result=}")
    return result


def run_partnership_agreement_ending_strategy(
    strategy: StrategyEnum, request: HttpRequest, partnership: Partnership, **kwargs: Any
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: partnership_agreement_ending_signal,
        StrategyEnum.UPDATE: partnership_agreement_ending_update_signal,
        StrategyEnum.CANCEL: partnership_agreement_ending_cancel_signal,
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


def get_scheduled_at(**kwargs: Unpack[PartnershipAgreementEndingKwargs]) -> datetime:
    return shift_date_and_apply_current_utc_time(
        kwargs["partnership"].agreement_end,
        offset=AGREEMENT_ENDING_OFFSET,
    )


def get_context(
    **kwargs: Unpack[PartnershipAgreementEndingKwargs],
) -> PartnershipAgreementEndingContext:
    return {"partnership": kwargs["partnership"]}


def get_context_json(context: PartnershipAgreementEndingContext) -> ContextModel:
    return ContextModel(
        {
            "partnership": api_model_url("partnership", context["partnership"].pk),
        },
    )


def get_generic_relation_object(
    context: PartnershipAgreementEndingContext,
    **kwargs: Unpack[PartnershipAgreementEndingKwargs],
) -> Partnership:
    return context["partnership"]


def get_recipients(
    context: PartnershipAgreementEndingContext,
    **kwargs: Unpack[PartnershipAgreementEndingKwargs],
) -> list[str]:
    partnership = context["partnership"]
    owners = AccountOwner.objects.filter(
        account_id=partnership.account_id, permission_type__in=ACCOUNT_OWNER_PERMISSION_TYPES_EXPECTED
    ).select_related("person")
    return [owner.person.email for owner in owners if owner.person.email]


def get_recipients_context_json(
    context: PartnershipAgreementEndingContext,
    **kwargs: Unpack[PartnershipAgreementEndingKwargs],
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


class PartnershipAgreementEndingReceiver(BaseAction):
    signal = partnership_agreement_ending_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[PartnershipAgreementEndingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[PartnershipAgreementEndingKwargs]) -> PartnershipAgreementEndingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: PartnershipAgreementEndingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> Partnership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class PartnershipAgreementEndingUpdateReceiver(BaseActionUpdate):
    signal = partnership_agreement_ending_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[PartnershipAgreementEndingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[PartnershipAgreementEndingKwargs]) -> PartnershipAgreementEndingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: PartnershipAgreementEndingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> Partnership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class PartnershipAgreementEndingCancelReceiver(BaseActionCancel):
    signal = partnership_agreement_ending_cancel_signal.signal_name

    def get_context(self, **kwargs: Unpack[PartnershipAgreementEndingKwargs]) -> PartnershipAgreementEndingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: PartnershipAgreementEndingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> Partnership:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: PartnershipAgreementEndingContext,
        **kwargs: Unpack[PartnershipAgreementEndingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

partnership_agreement_ending_receiver = PartnershipAgreementEndingReceiver()
partnership_agreement_ending_signal.connect(partnership_agreement_ending_receiver)


partnership_agreement_ending_update_receiver = PartnershipAgreementEndingUpdateReceiver()
partnership_agreement_ending_update_signal.connect(partnership_agreement_ending_update_receiver)


partnership_agreement_ending_cancel_receiver = PartnershipAgreementEndingCancelReceiver()
partnership_agreement_ending_cancel_signal.connect(partnership_agreement_ending_cancel_receiver)
