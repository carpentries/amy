import django_filters

from src.fiscal.models import Partnership
from src.offering.models import Account, Benefit
from src.workshops.filters import AMYFilterSet
from src.workshops.models import Curriculum


class AccountFilter(AMYFilterSet):
    active = django_filters.BooleanFilter("active")  # type: ignore
    account_type = django_filters.ChoiceFilter(choices=Account.AccountTypeChoices.choices)  # type: ignore
    order_by = django_filters.OrderingFilter(
        fields=(
            "account_type",
            "generic_relation_content_type",
            "generic_relation",
        )
    )  # type: ignore


class BenefitFilter(AMYFilterSet):
    active = django_filters.BooleanFilter("active")  # type: ignore
    unit_type = django_filters.ChoiceFilter(choices=Benefit.UNIT_TYPE_CHOICES)  # type: ignore
    order_by = django_filters.OrderingFilter(
        fields=(
            "name",
            "description",
            "created_at",
            "last_modified_at",
        )
    )  # type: ignore


class AccountBenefitFilter(AMYFilterSet):
    account = django_filters.ModelChoiceFilter(queryset=Account.objects.all())  # type: ignore
    partnership = django_filters.ModelChoiceFilter(queryset=Partnership.objects.all())  # type: ignore
    benefit = django_filters.ModelChoiceFilter(queryset=Benefit.objects.all())  # type: ignore
    curriculum = django_filters.ModelChoiceFilter(queryset=Curriculum.objects.all())  # type: ignore
    order_by = django_filters.OrderingFilter(
        fields=(
            "account",
            "benefit",
            "start_date",
            "end_date",
            "allocation",
            "created_at",
            "last_modified_at",
        )
    )  # type: ignore
