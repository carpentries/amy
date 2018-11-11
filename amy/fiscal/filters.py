from datetime import date

from dal_select2.widgets import (
    Select2,
    Select2Multiple,
)
import django_filters
from django.forms import widgets

from workshops.models import (
    Organization,
    Membership,
)
from workshops.filters import AMYFilterSet, AllCountriesFilter


class OrganizationFilter(AMYFilterSet):
    country = AllCountriesFilter(widget=Select2())

    membership__variant = django_filters.MultipleChoiceFilter(
        label='Memberships (current or past)',
        choices=Membership.MEMBERSHIP_CHOICES,
        widget=Select2Multiple(),
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            'fullname',
            'domain',
        ),
    )

    class Meta:
        model = Organization
        fields = [
            'country',
        ]


def filter_active_memberships_only(queryset, name, active):
    """Limit Memberships to only active entries."""
    if active:
        today = date.today()
        return queryset.filter(agreement_start__lte=today,
                               agreement_end__gte=today)
    else:
        return queryset


def filter_training_seats_only(queryset, name, seats):
    """Limit Memberships to only entries with some training seats allowed."""
    if seats:
        return queryset.filter(instructor_training_seats_total__gt=0)
    else:
        return queryset


def filter_nonpositive_remaining_seats(queryset, name, seats):
    """Limit Memberships to only entries with negative remaining seats."""
    if seats:
        return queryset.filter(instructor_training_seats_remaining__lt=0)
    else:
        return queryset


class MembershipFilter(AMYFilterSet):
    organization_name = django_filters.CharFilter(
        label='Organization name',
        field_name='organization__fullname',
        lookup_expr='icontains',
    )

    MEMBERSHIP_CHOICES = (('', 'Any'),) + Membership.MEMBERSHIP_CHOICES
    variant = django_filters.ChoiceFilter(choices=MEMBERSHIP_CHOICES)

    CONTRIBUTION_CHOICES = (('', 'Any'),) + Membership.CONTRIBUTION_CHOICES
    contribution_type = django_filters.ChoiceFilter(
        choices=CONTRIBUTION_CHOICES)

    active_only = django_filters.BooleanFilter(
        label='Only show active memberships',
        method=filter_active_memberships_only,
        widget=widgets.CheckboxInput)

    training_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with non-zero allowed training seats',
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput)

    nonpositive_remaining_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with zero or less remaining seats',
        method=filter_nonpositive_remaining_seats,
        widget=widgets.CheckboxInput)

    order_by = django_filters.OrderingFilter(
        fields=(
            'organization__fullname',
            'organization__domain',
            'agreement_start',
            'agreement_end',
            'instructor_training_seats_remaining',
        ),
    )

    class Meta:
        model = Membership
        fields = [
            'organization_name',
            'variant',
            'contribution_type',
        ]


class MembershipTrainingsFilter(AMYFilterSet):
    organization_name = django_filters.CharFilter(
        label='Organization name',
        field_name='organization__fullname',
        lookup_expr='icontains',
    )

    active_only = django_filters.BooleanFilter(
        label='Only show active memberships',
        method=filter_active_memberships_only,
        widget=widgets.CheckboxInput)

    training_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with non-zero allowed training seats',
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput)

    nonpositive_remaining_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with zero or less remaining seats',
        method=filter_nonpositive_remaining_seats,
        widget=widgets.CheckboxInput)

    order_by = django_filters.OrderingFilter(
        fields=(
            'organization__fullname',
            'organization__domain',
            'agreement_start',
            'agreement_end',
            'instructor_training_seats_total',
            'instructor_training_seats_utilized',
            'instructor_training_seats_remaining',
        ),
    )

    class Meta:
        model = Membership
        fields = [
            'organization_name',
        ]
