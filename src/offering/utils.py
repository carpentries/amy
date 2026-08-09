from dataclasses import dataclass, field
from typing import Annotated
from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet
from django_stubs_ext import Annotations

from src.fiscal.models import Partnership, PartnershipCreditsUsage
from src.offering.models import Account, AccountBenefit, AccountOwner
from src.workshops.models import Person

AnnotatedPartnership = Annotated[Partnership, Annotations[PartnershipCreditsUsage]]


@dataclass
class AccountBenefitSummary:
    """A single account benefit paired with its allocation usage."""

    account_benefit: AccountBenefit
    used: int

    @property
    def remaining(self) -> int:
        return max(self.account_benefit.allocation - self.used, 0)


@dataclass
class AccountBenefitStats:
    """Aggregated usage of all account benefits of a single account."""

    benefits_total: int = 0
    benefits_active: int = 0
    seats_allocated: int = 0
    seats_used: int = 0
    events_allocated: int = 0
    events_used: int = 0
    credits_allowed: int = 0
    credits_used: int = 0

    @property
    def seats_remaining(self) -> int:
        return max(self.seats_allocated - self.seats_used, 0)

    @property
    def events_remaining(self) -> int:
        return max(self.events_allocated - self.events_used, 0)

    @property
    def credits_remaining(self) -> int:
        return max(self.credits_allowed - self.credits_used, 0)


@dataclass
class OwnedAccountSummary:
    """Read-only view of a single account owned by a person."""

    account: Account
    permission_types: list[str] = field(default_factory=list)
    partnerships: list[AnnotatedPartnership] = field(default_factory=list)
    account_benefits: list[AccountBenefitSummary] = field(default_factory=list)
    stats: AccountBenefitStats = field(default_factory=AccountBenefitStats)


def owned_accounts_queryset(person: Person) -> QuerySet[AccountOwner]:
    """Active ownership records of active accounts held by `person`.

    Individual accounts are left out: they have no partnerships, and their benefits are
    presented to the person elsewhere."""
    return AccountOwner.objects.filter(
        person=person,
        active=True,
        account__active=True,
        account__account_type__in=[
            Account.AccountTypeChoices.ORGANISATION,
            Account.AccountTypeChoices.CONSORTIUM,
        ],
    )


def is_account_owner(person: Person | AnonymousUser) -> bool:
    """Check if `person` owns any active organisation or consortium account."""
    if not person.is_authenticated:
        return False
    return owned_accounts_queryset(person).exists()


def get_owned_account_summaries(person: Person) -> list[OwnedAccountSummary]:
    """Collect partnerships, account benefits and benefit usage stats for every account
    owned by `person`."""
    summaries: dict[UUID, OwnedAccountSummary] = {}

    owners = (
        owned_accounts_queryset(person).select_related("account").order_by("account__created_at", "permission_type")
    )
    for owner in owners:
        summary = summaries.setdefault(owner.account.pk, OwnedAccountSummary(account=owner.account))
        summary.permission_types.append(owner.get_permission_type_display())

    if not summaries:
        return []

    partnerships = (
        Partnership.objects.credits_usage_annotation()
        .filter(account__in=summaries.keys())
        .select_related("tier", "partner_consortium", "partner_organisation")
        .order_by("-agreement_start", "name")
    )
    for partnership in partnerships:
        summary = summaries[partnership.account_id]
        summary.partnerships.append(partnership)
        summary.stats.credits_allowed += partnership.credits
        summary.stats.credits_used += partnership.credits_used

    account_benefits = (
        AccountBenefit.objects.usage_annotation()
        .filter(account__in=summaries.keys())
        .select_related("benefit", "partnership", "curriculum", "discount")
        .order_by("-start_date", "benefit__name")
    )
    for account_benefit in account_benefits:
        summary = summaries[account_benefit.account_id]
        stats = summary.stats

        if account_benefit.benefit.unit_type == "seat":
            used = account_benefit.seats_used
            stats.seats_allocated += account_benefit.allocation
            stats.seats_used += used
        else:
            used = account_benefit.events_used
            stats.events_allocated += account_benefit.allocation
            stats.events_used += used

        stats.benefits_total += 1
        if account_benefit.active() and not account_benefit.frozen:
            stats.benefits_active += 1

        summary.account_benefits.append(AccountBenefitSummary(account_benefit=account_benefit, used=used))

    return list(summaries.values())
