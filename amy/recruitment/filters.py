from django.db.models import QuerySet
import django_filters as filters

from workshops.fields import ModelSelect2Widget, Select2MultipleWidget
from workshops.filters import AllCountriesMultipleFilter, AMYFilterSet
from workshops.forms import SELECT2_SIDEBAR
from workshops.models import Curriculum, Person

from .models import InstructorRecruitment


class InstructorRecruitmentFilter(AMYFilterSet):
    assigned_to = filters.ModelChoiceFilter(
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="admin-lookup", attrs=SELECT2_SIDEBAR),
    )

    online_inperson = filters.ChoiceFilter(
        choices=(
            ("online", "Online only"),
            ("inperson", "Inperson only"),
        ),
        empty_label="Any",
        label="Online/inperson",
        method="filter_online_inperson",
    )

    country = AllCountriesMultipleFilter(field_name="event__country", widget=Select2MultipleWidget)

    curricula = filters.ModelMultipleChoiceFilter(
        field_name="event__curricula",
        queryset=Curriculum.objects.all(),
        label="Curriculum",
        widget=Select2MultipleWidget(),
    )

    order_by = filters.OrderingFilter(
        fields=("event__start",),
        choices=(
            ("-calculated_priority", "Priority"),
            ("event__start", "Event start"),
            ("-event__start", "Event start (descending)"),
        ),
        method="filter_order_by",
    )

    class Meta:
        model = InstructorRecruitment
        fields = [
            "assigned_to",
            "status",
        ]

    def filter_online_inperson(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter recruitments based on the event (online/inperson) status."""
        if value == "online":
            return queryset.filter(event__tags__name="online")
        elif value == "inperson":
            return queryset.exclude(event__tags__name="online")
        else:
            return queryset

    def filter_order_by(self, queryset: QuerySet, name: str, values: list) -> QuerySet:
        return queryset.order_by(*values)
