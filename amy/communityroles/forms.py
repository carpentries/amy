from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from workshops.fields import ModelSelect2Widget
from workshops.forms import SELECT2_SIDEBAR, BootstrapHelper, WidgetOverrideMixin

from .models import CommunityRole, CommunityRoleConfig


class CommunityRoleForm(WidgetOverrideMixin, forms.ModelForm):
    class Meta:
        model = CommunityRole
        fields = (
            "config",
            "person",
            "award",
            "start",
            "end",
            "inactivation",
            "membership",
            "url",
            "generic_relation_m2m",
        )
        widgets = {
            "person": ModelSelect2Widget(
                data_view="person-lookup", attrs=SELECT2_SIDEBAR
            ),
            "award": ModelSelect2Widget(
                data_view="award-lookup", attrs=SELECT2_SIDEBAR
            ),
            "membership": ModelSelect2Widget(
                data_view="membership-lookup", attrs=SELECT2_SIDEBAR
            ),
        }

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        super().__init__(*args, **kwargs)
        bootstrap_kwargs = {
            "add_cancel_button": False,
            "form_tag": form_tag,
        }
        self.helper = BootstrapHelper(**bootstrap_kwargs)

    def clean(self) -> dict[str, Any]:
        """Validate form according to rules set up in related Community Role
        configuration."""
        config: CommunityRoleConfig = self.cleaned_data["config"]

        # Award required?
        if config.link_to_award and not self.cleaned_data["award"]:
            raise ValidationError(f"Award is required with community role {config}")

        # Specific award role required?
        if (badge := config.award_badge_limit) and (
            award := self.cleaned_data["award"]
        ):
            if award.badge != badge:
                raise ValidationError(
                    f"Award badge must be {badge!r} for community role {config}"
                )

        # Membership required?
        if config.link_to_membership and not self.cleaned_data["membership"]:
            raise ValidationError(
                f"Membership is required with community role {config}"
            )

        # Additional URL supported?
        if not config.additional_url and self.cleaned_data["url"]:
            raise ValidationError(f"URL is not supported for community role {config}")

        # Multiple items supported for the generic relation?
        generic_relation_ids = set(self.cleaned_data["generic_relation_m2m"])
        if not config.generic_relation_multiple_items and len(generic_relation_ids) > 1:
            raise ValidationError(
                "Multiple (>1) generic items are not supported for "
                f"community role {config}"
            )

        # Generic relation objects don't exist?
        model_class = config.generic_relation_content_type.model_class()
        objects = model_class._base_manager.filter(id__in=generic_relation_ids)
        object_ids = {object.id for object in set(objects)}
        if missing_ids := object_ids - generic_relation_ids:
            raise ValidationError(
                f"Some generic relation objects of model {model_class!r} "
                f"don't exist: {missing_ids}"
            )

        return super().clean()
