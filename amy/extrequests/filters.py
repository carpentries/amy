from datetime import date
import re

from django.db.models import Case, F, Q, QuerySet, When
from django.forms import widgets
from django.http import QueryDict
import django_filters

from extrequests.models import SelfOrganisedSubmission, WorkshopInquiryRequest
from workshops.fields import Select2Widget
from workshops.filters import (
    AllCountriesFilter,
    AMYFilterSet,
    ContinentFilter,
    ForeignKeyAllValuesFilter,
    NamesOrderingFilter,
    StateFilterSet,
)
from workshops.models import Curriculum, Person, TrainingRequest, WorkshopRequest

# ------------------------------------------------------------
# TrainingRequest related filter and filter methods
# ------------------------------------------------------------


class TrainingRequestFilter(AMYFilterSet):
    def __init__(self, data=None, *args, **kwargs):
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
        field_name="member_code", lookup_expr="icontains", label="Member code"
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
        field_name="member_code_override",
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
            "state",
            "matched",
            "affiliation",
            "location",
        ]

    def filter_matched(self, queryset, name, choice):
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

    def filter_by_person(self, queryset, name, value):
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

    def filter_affiliation(self, queryset, name, affiliation):
        if affiliation == "":
            return queryset
        else:
            q = Q(affiliation__icontains=affiliation) | Q(
                person__affiliation__icontains=affiliation
            )
            return queryset.filter(q).distinct()

    def filter_training_requests_by_state(self, queryset, name, choice):
        if choice == "pa":
            return queryset.filter(state__in=["p", "a"])
        else:
            return queryset.filter(state=choice)

    def filter_non_null_manual_score(self, queryset, name, manual_score):
        if manual_score:
            return queryset.filter(score_manual__isnull=False)
        return queryset


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
        self, queryset: QuerySet, name: str, apply_filter: bool
    ) -> QuerySet:
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
