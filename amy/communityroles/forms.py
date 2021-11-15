from collections import defaultdict
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
        cleaned_data = super().clean()
        errors: defaultdict[str, list[ValidationError]] = defaultdict(list)
        config: CommunityRoleConfig = cleaned_data["config"]

        # Award required?
        if config.link_to_award and not cleaned_data["award"]:
            errors["award"].append(
                ValidationError(f"Award is required with community role {config}")
            )

        # Specific award badge required?
        if (badge := config.award_badge_limit) and (award := cleaned_data["award"]):
            if award.badge != badge:
                errors["award"].append(
                    ValidationError(
                        f"Award badge must be {badge} for community role {config}"
                    )
                )

        # Membership required?
        if config.link_to_membership and not cleaned_data["membership"]:
            errors["membership"].append(
                ValidationError(f"Membership is required with community role {config}")
            )

        # Additional URL supported?
        if not config.additional_url and cleaned_data["url"]:
            errors["url"].append(
                ValidationError(f"URL is not supported for community role {config}")
            )

        # Multiple items supported for the generic relation?
        generic_relation_ids = set(cleaned_data["generic_relation_m2m"])
        if not config.generic_relation_multiple_items and len(generic_relation_ids) > 1:
            errors["generic_relation_m2m"].append(
                ValidationError(
                    "Multiple (>1) generic items are not supported for "
                    f"community role {config}"
                )
            )

        # Generic relation objects don't exist?
        if config.generic_relation_content_type:
            # limit provided IDs to not leak any database information
            generic_relation_ids = (
                set(cleaned_data["generic_relation_m2m"][0:1])
                if not config.generic_relation_multiple_items
                else set(cleaned_data["generic_relation_m2m"][:])
            )
            model_class = config.generic_relation_content_type.model_class()
            objects = model_class._base_manager.filter(id__in=generic_relation_ids)
            object_ids = {object.id for object in set(objects)}
            if missing_ids := generic_relation_ids - object_ids:
                errors["generic_relation_m2m"].append(
                    ValidationError(
                        f"Some generic relation objects of model {model_class.__name__}"
                        f" don't exist: {missing_ids}"
                    )
                )

        if errors:
            raise ValidationError(errors)

        return cleaned_data
