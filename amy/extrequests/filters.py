import re

from django.db.models import Q
from django.forms import widgets
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
    search = django_filters.CharFilter(
        label="Name or Email",
        method="filter_by_person",
    )

    group_name = django_filters.CharFilter(
        field_name="group_name", lookup_expr="icontains", label="Group"
    )

    state = django_filters.ChoiceFilter(
        label="State",
        choices=(("no_d", "Pending or accepted"),) + TrainingRequest.STATE_CHOICES,
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
            "group_name",
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
        if choice == "no_d":
            return queryset.exclude(state="d")
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
