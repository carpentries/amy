import re
from datetime import date
from typing import Any

import django_filters
from django.db.models import Case, F, Q, QuerySet, When
from django.forms import widgets
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

from src.extrequests.models import SelfOrganisedSubmission, WorkshopInquiryRequest
from src.extrequests.utils import get_eventbrite_id_from_url_or_return_input
from src.workshops.fields import Select2Widget
from src.workshops.filters import (
    AllCountriesFilter,
    AMYFilterSet,
    ContinentFilter,
    ForeignKeyAllValuesFilter,
    NamesOrderingFilter,
    StateFilterSet,
)
from src.workshops.models import Curriculum, Person, TrainingRequest, WorkshopRequest

# ------------------------------------------------------------
# TrainingRequest related filter and filter methods
# ------------------------------------------------------------


class TrainingRequestFilter(AMYFilterSet):
    def __init__(self, data: MultiValueDict[str, str] | None = None, *args: Any, **kwargs: Any) -> None:
        # If no filters are set, use some default settings.
        # This avoids handling the full list of training requests
        # client-side unless the user deliberately chooses to do so.
        # See https://github.com/carpentries/amy/issues/2314
        if not data:
            data = QueryDict("state=pa&matched=u")

        super().__init__(data, *args, **kwargs)

    search = django_filters.CharFilter(
        label="Name or Email",
        method="filter_by_person",
    )

    member_code = django_filters.CharFilter(
        field_name="member_code",
        lookup_expr="icontains",
        label="Member code",
    )

    eventbrite_id = django_filters.CharFilter(
        label="Eventbrite ID or URL",
        method="filter_eventbrite_id",
    )

    state = django_filters.ChoiceFilter(
        label="State",
        choices=(("pa", "Pending or accepted"),) + TrainingRequest.STATE_CHOICES,
        method="filter_training_requests_by_state",
    )

    matched = django_filters.ChoiceFilter(
        label="Is Matched?",
        choices=(
            ("", "Unknown"),
            ("u", "Unmatched"),
            ("p", "Matched trainee, unmatched training"),
            ("t", "Matched trainee and training"),
        ),
        method="filter_matched",
    )

    nonnull_manual_score = django_filters.BooleanFilter(
        label="Manual score applied",
        method="filter_non_null_manual_score",
        widget=widgets.CheckboxInput,
    )

    invalid_member_code = django_filters.BooleanFilter(
        label="Member code marked as invalid",
        method="filter_member_code_override",
        widget=widgets.CheckboxInput,
    )

    affiliation = django_filters.CharFilter(
        method="filter_affiliation",
    )

    location = django_filters.CharFilter(lookup_expr="icontains")

    order_by = NamesOrderingFilter(
        fields=(
            "created_at",
            "score_total",
        ),
    )

    class Meta:
        model = TrainingRequest
        fields = [
            "search",
            "member_code",
            "invalid_member_code",
            "state",
            "matched",
            "affiliation",
            "location",
        ]

    def filter_matched(self, queryset: QuerySet[TrainingRequest], name: str, choice: str) -> QuerySet[TrainingRequest]:
        if choice == "":
            return queryset
        elif choice == "u":  # unmatched
            return queryset.filter(person=None)
        elif choice == "p":  # matched trainee, unmatched training
            return (
                queryset.filter(person__isnull=False)
                .exclude(
                    person__task__role__name="learner",
                    person__task__event__tags__name="TTT",
                )
                .distinct()
            )
        else:  # choice == 't' <==> matched trainee and training
            return queryset.filter(
                person__task__role__name="learner",
                person__task__event__tags__name="TTT",
            ).distinct()

    def filter_by_person(self, queryset: QuerySet[TrainingRequest], name: str, value: str) -> QuerySet[TrainingRequest]:
        if value == "":
            return queryset
        else:
            # 'Harry Potter' -> ['Harry', 'Potter']
            tokens = re.split(r"\s+", value)
            # Each token must match email address or github username or
            # personal, or family name.
            for token in tokens:
                queryset = queryset.filter(
                    Q(personal__icontains=token)
                    | Q(middle__icontains=token)
                    | Q(family__icontains=token)
                    | Q(email__icontains=token)
                    | Q(person__personal__icontains=token)
                    | Q(person__middle__icontains=token)
                    | Q(person__family__icontains=token)
                    | Q(person__email__icontains=token)
                )
            return queryset

    def filter_affiliation(
        self, queryset: QuerySet[TrainingRequest], name: str, affiliation: str
    ) -> QuerySet[TrainingRequest]:
        if affiliation == "":
            return queryset
        else:
            q = Q(affiliation__icontains=affiliation) | Q(person__affiliation__icontains=affiliation)
            return queryset.filter(q).distinct()

    def filter_training_requests_by_state(
        self, queryset: QuerySet[TrainingRequest], name: str, choice: str
    ) -> QuerySet[TrainingRequest]:
        if choice == "pa":
            return queryset.filter(state__in=["p", "a"])
        else:
            return queryset.filter(state=choice)

    def filter_non_null_manual_score(
        self, queryset: QuerySet[TrainingRequest], name: str, manual_score: bool
    ) -> QuerySet[TrainingRequest]:
        if manual_score:
            return queryset.filter(score_manual__isnull=False)
        return queryset

    def filter_member_code_override(
        self, queryset: QuerySet[TrainingRequest], name: str, only_overrides: bool
    ) -> QuerySet[TrainingRequest]:
        """If checked, only show requests where the member code has been
        marked as invalid. Otherwise, show all requests."""
        if only_overrides:
            return queryset.filter(member_code_override=True)
        return queryset

    def filter_eventbrite_id(
        self, queryset: QuerySet[TrainingRequest], name: str, value: str
    ) -> QuerySet[TrainingRequest]:
        """
        Returns the queryset filtered by an Eventbrite ID or URL.
        Events have multiple possible URLs which all contain the ID, so
        if a URL is used, the filter will try to extract and filter by the ID.
        If no ID can be found, the filter will use the original input.
        """

        try:
            # if input is an integer, assume it to be a partial or full Eventbrite ID
            int(value)
        except ValueError:
            # otherwise, try to extract an ID from the input
            value = get_eventbrite_id_from_url_or_return_input(value)

        return queryset.filter(eventbrite_url__icontains=value)


# ------------------------------------------------------------
# WorkshopRequest related filter and filter methods
# ------------------------------------------------------------


class WorkshopRequestFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2Widget)
    country = AllCountriesFilter(widget=Select2Widget)
    continent = ContinentFilter(widget=Select2Widget, label="Continent")
    requested_workshop_types = django_filters.ModelMultipleChoiceFilter(
        label="Requested workshop types",
        queryset=Curriculum.objects.all(),
        widget=widgets.CheckboxSelectMultiple(),
    )
    unused_member_code = django_filters.BooleanFilter(
        label="Institution has an active member code but did not provide it",
        method="filter_unused_member_code",
        widget=widgets.CheckboxInput(),
    )

    order_by = django_filters.OrderingFilter(
        fields=("created_at",),
    )

    class Meta:
        model = WorkshopRequest
        fields = [
            "state",
            "assigned_to",
            "requested_workshop_types",
            "country",
        ]

    def filter_unused_member_code(
        self, queryset: QuerySet[WorkshopRequest], name: str, apply_filter: bool
    ) -> QuerySet[WorkshopRequest]:
        if apply_filter:
            # find requests where no member code was provided
            requests_without_code = queryset.filter(member_code="")

            # find requests where institution has an active membership
            # ideally compare to workshop dates, but fall back on today
            return requests_without_code.annotate(
                date_to_check=Case(
                    When(
                        preferred_dates__isnull=False,
                        then=F("preferred_dates"),
                    ),
                    default=date.today(),
                )
            ).filter(
                institution__memberships__agreement_end__gte=F("date_to_check"),
                institution__memberships__agreement_start__lte=F("date_to_check"),
            )
        return queryset


# ------------------------------------------------------------
# WorkshopInquiryRequest related filter and filter methods
# ------------------------------------------------------------


class WorkshopInquiryFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2Widget)
    country = AllCountriesFilter(widget=Select2Widget)
    continent = ContinentFilter(widget=Select2Widget, label="Continent")
    requested_workshop_types = django_filters.ModelMultipleChoiceFilter(
        label="Requested workshop types",
        queryset=Curriculum.objects.all(),
        widget=widgets.CheckboxSelectMultiple(),
    )

    order_by = django_filters.OrderingFilter(
        fields=("created_at",),
    )

    class Meta:
        model = WorkshopInquiryRequest
        fields = [
            "state",
            "assigned_to",
            "requested_workshop_types",
            "country",
        ]


# ------------------------------------------------------------
# SelfOrganisedSubmission related filter and filter methods
# ------------------------------------------------------------


class SelfOrganisedSubmissionFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2Widget)
    country = AllCountriesFilter(widget=Select2Widget)
    continent = ContinentFilter(widget=Select2Widget, label="Continent")
    workshop_types = django_filters.ModelMultipleChoiceFilter(
        label="Requested workshop types",
        queryset=Curriculum.objects.all(),
        widget=widgets.CheckboxSelectMultiple(),
    )

    order_by = django_filters.OrderingFilter(
        fields=("created_at",),
    )

    class Meta:
        model = SelfOrganisedSubmission
        fields = [
            "state",
            "assigned_to",
            "workshop_types",
            "workshop_format",
        ]
