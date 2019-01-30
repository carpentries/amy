from dal import autocomplete
import django_filters

from extrequests.models import (
    EventRequest,
    EventSubmission,
    DCSelfOrganizedEventRequest,
)
from workshops.fields import Select2
from workshops.filters import (
    AMYFilterSet,
    StateFilterSet,
    ForeignKeyAllValuesFilter,
    AllCountriesFilter,
)
from workshops.forms import SIDEBAR_DAL_WIDTH
from workshops.models import (
    Organization,
    Person,
)


# ------------------------------------------------------------
# EventRequest related filter and filter methods
# CAUTION: THIS FEATURE IS DEPRECATED!!!
# ------------------------------------------------------------

class EventRequestFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2())
    country = AllCountriesFilter(widget=Select2())
    workshop_type = django_filters.ChoiceFilter(
        choices=(('swc', 'Software-Carpentry'),
                 ('dc', 'Data-Carpentry')),
        label='Workshop type',
        empty_label='All',
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            'created_at',
        ),
    )

    class Meta:
        model = EventRequest
        fields = [
            'state',
            'assigned_to',
            'workshop_type',
            'country',
        ]


# ------------------------------------------------------------
# EventSubmission related filter and filter methods
# CAUTION: THIS FEATURE IS DEPRECATED!!!
# ------------------------------------------------------------

class EventSubmissionFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2())

    order_by = django_filters.OrderingFilter(
        fields=(
            'created_at',
        ),
    )

    class Meta:
        model = EventSubmission
        fields = [
            'state',
            'assigned_to',
        ]


# -------------------------------------------------------------
# DCSelfOrganizedEventRequest related filter and filter methods
# CAUTION: THIS FEATURE IS DEPRECATED!!!
# -------------------------------------------------------------

class DCSelfOrganizedEventRequestFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2())

    order_by = django_filters.OrderingFilter(
        fields=(
            'created_at',
        ),
    )

    class Meta:
        model = DCSelfOrganizedEventRequest
        fields = [
            'state',
            'assigned_to',
        ]
        order_by = [
            '-created_at', 'created_at',
        ]
