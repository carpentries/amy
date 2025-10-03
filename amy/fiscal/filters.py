from datetime import date
from typing import Annotated

from django.db.models import F, QuerySet
from django.forms import widgets
import django_filters
from django_stubs_ext import Annotations

from fiscal.models import Consortium, Partnership, PartnershipCreditsUsage
from workshops.fields import Select2MultipleWidget, Select2Widget
from workshops.filters import AllCountriesFilter, AMYFilterSet
from workshops.models import Membership, MembershipSeatUsage, Organization


class OrganizationFilter(AMYFilterSet):
    country = AllCountriesFilter(widget=Select2Widget)

    memberships__variant = django_filters.MultipleChoiceFilter(  # type: ignore
        label="Memberships (current or past)",
        choices=Membership.MEMBERSHIP_CHOICES,
        widget=Select2MultipleWidget,
    )

    order_by = django_filters.OrderingFilter(  # type: ignore
        fields=(
            "fullname",
            "domain",
        ),
    )

    class Meta:
        model = Organization
        fields = [
            "country",
        ]


def filter_active_memberships_only(queryset: QuerySet[Membership], name: str, active: bool) -> QuerySet[Membership]:
    """Limit Memberships to only active entries."""
    if active:
        today = date.today()
        return queryset.filter(agreement_start__lte=today, agreement_end__gte=today)
    else:
        return queryset


def filter_training_seats_only(
    queryset: QuerySet[Annotated["Membership", Annotations[MembershipSeatUsage]]], name: str, seats: bool
) -> QuerySet[Annotated["Membership", Annotations[MembershipSeatUsage]]]:
    """Limit Memberships to only entries with some training seats allowed."""
    if seats:
        return queryset.filter(instructor_training_seats_total__gt=0)
    else:
        return queryset


def filter_negative_remaining_seats(
    queryset: QuerySet[Annotated["Membership", Annotations[MembershipSeatUsage]]], name: str, seats: bool
) -> QuerySet[Annotated["Membership", Annotations[MembershipSeatUsage]]]:
    """Limit Memberships to only entries with negative remaining seats."""
    if seats:
        return queryset.filter(instructor_training_seats_remaining__lt=0)
    else:
        return queryset


class MembershipFilter(AMYFilterSet):
    organization_name = django_filters.CharFilter(  # type: ignore
        label="Organization name",
        field_name="organizations__fullname",
        lookup_expr="icontains",
    )

    MEMBERSHIP_CHOICES = (("", "Any"),) + Membership.MEMBERSHIP_CHOICES
    variant = django_filters.ChoiceFilter(choices=MEMBERSHIP_CHOICES)  # type: ignore

    CONTRIBUTION_CHOICES = (("", "Any"),) + Membership.CONTRIBUTION_CHOICES
    contribution_type = django_filters.ChoiceFilter(choices=CONTRIBUTION_CHOICES)  # type: ignore

    active_only = django_filters.BooleanFilter(  # type: ignore
        label="Only show active memberships",
        method=filter_active_memberships_only,
        widget=widgets.CheckboxInput,
    )

    training_seats_only = django_filters.BooleanFilter(  # type: ignore
        label="Only show memberships with more than zero allowed training seats",
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput,
    )

    negative_remaining_seats_only = django_filters.BooleanFilter(  # type: ignore
        label="Only show memberships with less than zero remaining seats",
        method=filter_negative_remaining_seats,
        widget=widgets.CheckboxInput,
    )

    order_by = django_filters.OrderingFilter(  # type: ignore
        fields=(
            "agreement_start",
            "agreement_end",
            "instructor_training_seats_remaining",
        ),
    )

    class Meta:
        model = Membership
        fields = [
            "organization_name",
            "consortium",
            "public_status",
            "variant",
            "contribution_type",
        ]


class MembershipTrainingsFilter(AMYFilterSet):
    organization_name = django_filters.CharFilter(  # type: ignore
        label="Organization name",
        field_name="organizations__fullname",
        lookup_expr="icontains",
    )

    active_only = django_filters.BooleanFilter(  # type: ignore
        label="Only show active memberships",
        method=filter_active_memberships_only,
        widget=widgets.CheckboxInput,
    )

    training_seats_only = django_filters.BooleanFilter(  # type: ignore
        label="Only show memberships with more than zero allowed training seats",
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput,
    )

    negative_remaining_seats_only = django_filters.BooleanFilter(  # type: ignore
        label="Only show memberships with less than zero remaining seats",
        method=filter_negative_remaining_seats,
        widget=widgets.CheckboxInput,
    )

    order_by = django_filters.OrderingFilter(  # type: ignore
        fields=(
            "name",
            "agreement_start",
            "agreement_end",
            "instructor_training_seats_total",
            "instructor_training_seats_utilized",
            "instructor_training_seats_remaining",
        ),
    )

    class Meta:
        model = Membership
        fields = [
            "organization_name",
        ]


def filter_consortium_organisation_contain(
    queryset: QuerySet[Consortium], name: str, organisations: list[Organization]
) -> QuerySet[Consortium]:
    if organisations:
        return queryset.filter(organisations__in=organisations)
    else:
        return queryset


class ConsortiumFilter(AMYFilterSet):
    contains_organisations = django_filters.ModelMultipleChoiceFilter(
        queryset=Organization.objects.all(),
        method=filter_consortium_organisation_contain,
        label="Contains organisations",
    )  # type: ignore
    order_by = django_filters.OrderingFilter(
        fields=(
            "name",
            "description",
        )
    )  # type: ignore


def filter_currently_active_partnership(
    queryset: QuerySet[Partnership], name: str, active: bool
) -> QuerySet[Partnership]:
    if not active:
        return queryset

    today = date.today()
    return queryset.filter(agreement_start__lte=today, agreement_end__gte=today)


def filter_partnership_credits(
    queryset: QuerySet[Annotated["Partnership", Annotations[PartnershipCreditsUsage]]],
    name: str,
    selection: str,
) -> QuerySet[Partnership]:
    match selection:
        case "under_limit":
            return queryset.filter(credits_used__lt=F("credits"))
        case "over_limit":
            return queryset.filter(credits_used__gte=F("credits"))
    return queryset


class PartnershipFilter(AMYFilterSet):
    active_only = django_filters.BooleanFilter(  # type: ignore
        label="Show active only (current date between (start, end) dates)",
        method=filter_currently_active_partnership,
        widget=widgets.CheckboxInput,
    )

    credits = django_filters.ChoiceFilter(  # type: ignore
        label="Credits",
        choices=[
            ("under_limit", "under limit"),
            ("over_limit", "over limit"),
        ],
        method=filter_partnership_credits,
    )

    order_by = django_filters.OrderingFilter(fields=["name"])  # type: ignore

    class Meta:
        model = Partnership
        fields = [
            "tier",
        ]
