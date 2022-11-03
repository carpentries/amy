from django.db.models import F, QuerySet
from django.forms import widgets
import django_filters as filters

from recruitment.models import InstructorRecruitment
from workshops.fields import Select2MultipleWidget
from workshops.filters import AllCountriesMultipleFilter, AMYFilterSet
from workshops.models import Curriculum


class UpcomingTeachingOpportunitiesFilter(AMYFilterSet):
    status = filters.ChoiceFilter(
        choices=(
            ("online", "Online only"),
            ("inperson", "Inperson only"),
        ),
        empty_label="Any",
        label="Online/inperson",
        method="filter_status",
    )

    only_applied_to = filters.BooleanFilter(
        label="Show only workshops I have applied to",
        method="filter_application_only",
        widget=widgets.CheckboxInput,
    )

    country = AllCountriesMultipleFilter(
        field_name="event__country",
        widget=Select2MultipleWidget,
        extend_countries=False,
    )

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
            ("proximity", "Closer to my airport"),
            ("-proximity", "Further away from my airport"),
        ),
        method="filter_order_by",
    )

    class Meta:
        model = InstructorRecruitment
        fields = [
            "status",
        ]

    def filter_status(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter recruitments based on the event (online/inperson) status."""
        if value == "online":
            return queryset.filter(event__tags__name="online")
        elif value == "inperson":
            return queryset.exclude(event__tags__name="online")
        else:
            return queryset

    def filter_order_by(self, queryset: QuerySet, name: str, values: list) -> QuerySet:
        """Order entries by proximity to user's airport."""
        try:
            latitude: float = self.request.user.airport.latitude
        except AttributeError:
            latitude = 0.0

        try:
            longitude: float = self.request.user.airport.longitude
        except AttributeError:
            longitude = 0.0

        # `0.0` is neutral element for this equation, so even if user doesn't have the
        # airport specified, the sorting should still work
        distance = (F("event__latitude") - latitude) ** 2.0 + (
            F("event__longitude") - longitude
        ) ** 2.0

        if values == ["proximity"]:
            return queryset.annotate(distance=distance).order_by("distance")
        elif values == ["-proximity"]:
            return queryset.annotate(distance=distance).order_by("-distance")
        else:
            return queryset.order_by(*values)

    def filter_application_only(
        self, queryset: QuerySet, name: str, value: bool
    ) -> QuerySet:
        if value:
            return queryset.filter(signups__person=self.request.user)

        return queryset
