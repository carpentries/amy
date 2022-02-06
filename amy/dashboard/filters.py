from django.db.models import F
import django_filters as filters

from recruitment.models import InstructorRecruitment
from workshops.filters import AMYFilterSet


class ProximityOrderingFilter(filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        self.latitude: float = kwargs.pop("lat", 0.0)
        self.longitude: float = kwargs.pop("lng", 0.0)
        super().__init__(*args, **kwargs)

        self.extra["choices"] += [
            ("proximity", "Closer to my airport"),
            ("-proximity", "Further away from my airport"),
        ]

    def filter(self, qs, value: list):
        ordering = super().filter(qs, value)
        distance = (F("airport__latitude") - self.latitude) ** 2 + (
            F("airport__longitude") - self.longitude
        ) ** 2

        if not value:
            return ordering

        # `value` is a list
        if any(v in ["proximity"] for v in value):
            return ordering.annotate(distance=distance).order_by("distance")
        elif any(v in ["-proximity"] for v in value):
            return ordering.annotate(distance=distance).order_by("-distance")

        return ordering


class UpcomingTeachingOpportunitiesFilter(AMYFilterSet):
    status = filters.ChoiceFilter(
        choices=(
            ("any", "Any"),
            ("online", "Online only"),
            ("inperson", "Inperson only"),
        ),
        method="filter_status",
    )

    # TODO: pass user's lat/lng
    order_by = ProximityOrderingFilter(
        fields=(
            "event__start",
            "proximity",
        )
    )

    class Meta:
        model = InstructorRecruitment
        fields = [
            "status",
        ]

    def filter_status(self, queryset, name, value):
        """Filter recruitments based on the event (online/inperson) status."""
        if value == "any":
            return queryset
        elif value == "online":
            return queryset.filter(event__tags__name="online")
        elif value == "inperson":
            return queryset.exclude(event__tags__name="online")
