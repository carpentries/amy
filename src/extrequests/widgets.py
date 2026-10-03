from typing import Any, cast

from src.offering.models import Benefit
from src.workshops.fields import ModelSelect2Widget


class BenefitSelect2Widget(ModelSelect2Widget):
    """Select2 widget which exposes the `Benefit` behind every rendered option.

    Options fetched over AJAX carry the same information (see `AccountBenefitsLookupView`
    and `BenefitsLookupView` in `src.workshops.lookups`), so regardless of how an option
    ended up in the widget, the client can tell which benefit it maps to. This is used by
    the "Accept & match" confirmation modal in `requests/all_trainingrequests.html`.
    """

    def benefit_from_instance(self, instance: Any) -> Benefit:
        return cast(Benefit, instance)

    def create_option(
        self,
        name: str,
        value: Any,
        label: int | str,
        selected: bool,
        index: int,
        subindex: int | None = None,
        attrs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)

        # `value` is a `ModelChoiceIteratorValue` for every non-empty option.
        instance = getattr(value, "instance", None)
        if instance is not None:
            benefit = self.benefit_from_instance(instance)
            option["attrs"]["data-benefit-id"] = str(benefit.pk)
            option["attrs"]["data-benefit-name"] = benefit.name

        return option


class AccountBenefitSelect2Widget(BenefitSelect2Widget):
    """`BenefitSelect2Widget` for a widget listing `AccountBenefit`s."""

    def benefit_from_instance(self, instance: Any) -> Benefit:
        return cast(Benefit, instance.benefit)
