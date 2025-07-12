import django_filters

from workshops.filters import AMYFilterSet


class EventCategoryFilter(AMYFilterSet):
    order_by = django_filters.OrderingFilter(fields=("name",))  # type: ignore
