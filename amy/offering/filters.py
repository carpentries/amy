import django_filters

from offering.models import Account
from workshops.filters import AMYFilterSet


class AccountFilter(AMYFilterSet):
    account_type = django_filters.ChoiceFilter(choices=Account.ACCOUNT_TYPE_CHOICES)  # type: ignore
    order_by = django_filters.OrderingFilter(
        fields=(
            "account_type",
            "generic_relation_content_type",
            "generic_relation",
        )
    )  # type: ignore


class EventCategoryFilter(AMYFilterSet):
    order_by = django_filters.OrderingFilter(fields=("name",))  # type: ignore
