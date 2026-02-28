import django_filters

from src.fiscal.models import Partnership
from src.offering.models import Account, Benefit
from src.workshops.filters import AMYFilterSet
from src.workshops.models import Curriculum


class AccountFilter(AMYFilterSet):
    active = django_filters.BooleanFilter("active")
    account_type = django_filters.ChoiceFilter(choices=Account.AccountTypeChoices.choices)
    order_by = django_filters.OrderingFilter(
        fields=(
            "account_type",
            "generic_relation_content_type",
            "generic_relation",
        )
    )


class BenefitFilter(AMYFilterSet):
    active = django_filters.BooleanFilter("active")
    unit_type = django_filters.ChoiceFilter(choices=Benefit.UNIT_TYPE_CHOICES)
    order_by = django_filters.OrderingFilter(
        fields=(
            "name",
            "description",
            "created_at",
            "last_modified_at",
        )
    )


class AccountBenefitFilter(AMYFilterSet):
    account = django_filters.ModelChoiceFilter(queryset=Account.objects.all())
    partnership = django_filters.ModelChoiceFilter(queryset=Partnership.objects.all())
    benefit = django_filters.ModelChoiceFilter(queryset=Benefit.objects.all())
    curriculum = django_filters.ModelChoiceFilter(queryset=Curriculum.objects.all())
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
    )
