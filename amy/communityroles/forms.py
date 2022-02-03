from collections import defaultdict
from typing import Any, Optional

from django import forms
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from workshops.fields import HeavySelect2Widget, ModelSelect2Widget
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
            "generic_relation_content_type",
            "generic_relation_pk",
        )
        widgets = {
            "config": HeavySelect2Widget(
                data_view="api:communityroleconfig-list", attrs=SELECT2_SIDEBAR
            ),
            "person": ModelSelect2Widget(
                data_view="person-lookup", attrs=SELECT2_SIDEBAR
            ),
            "award": ModelSelect2Widget(
                data_view="award-lookup", attrs=SELECT2_SIDEBAR
            ),
            "membership": ModelSelect2Widget(
                data_view="membership-lookup", attrs=SELECT2_SIDEBAR
            ),
            "generic_relation_content_type": forms.Select(
                # "disabled" means the browsers will not send the field during POST.
                # See how it's handled in `clean()` method below.
                attrs={"disabled": ""},
            ),
            "generic_relation_pk": HeavySelect2Widget(
                data_view="generic-object-lookup", attrs=SELECT2_SIDEBAR
            ),
        }
        labels = {
            "generic_relation_content_type": "Generic relation object type",
            "generic_relation_pk": "Generic relation object",
        }

    class Media:
        js = ("communityrole_form.js",)

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
        config: Optional[CommunityRoleConfig] = cleaned_data.get("config")

        # Config is required, but field validation for 'config' should raise
        # validation error first.
        if not config:
            return cleaned_data

        # Award required?
        if config.link_to_award and not cleaned_data.get("award"):
            errors["award"].append(
                ValidationError(f"Award is required with community role {config}")
            )

        # Specific award badge required?
        if (badge := config.award_badge_limit) and (award := cleaned_data.get("award")):
            if award.badge != badge:
                errors["award"].append(
                    ValidationError(
                        f"Award badge must be {badge} for community role {config}"
                    )
                )

        # Membership required?
        if config.link_to_membership and not cleaned_data.get("membership"):
            errors["membership"].append(
                ValidationError(f"Membership is required with community role {config}")
            )

        # Additional URL supported?
        if not config.additional_url and cleaned_data.get("url"):
            errors["url"].append(
                ValidationError(f"URL is not supported for community role {config}")
            )

        # Widget for `generic_relation_content_type` is disabled in HTML, which
        # makes browsers not send it. The code below sets the default value to
        # the same value as in related config.
        generic_relation_content_type = config.generic_relation_content_type

        # Generic relation object must exist
        if config.generic_relation_content_type and generic_relation_content_type:
            model_class = generic_relation_content_type.model_class()
            try:
                model_class._base_manager.get(
                    pk=cleaned_data.get("generic_relation_pk")
                )
            except ObjectDoesNotExist:
                errors["generic_relation_pk"].append(
                    ValidationError(
                        f"Generic relation object of model {model_class.__name__} "
                        "doesn't exist"
                    )
                )

        if errors:
            raise ValidationError(errors)

        return cleaned_data

    def clean_end(self):
        '''Validate that end >= start'''
        start = self.cleaned_data.get("start")
        end = self.cleaned_data.get("end")
        if start and end and end < start:
            raise ValidationError(f"Must not be earlier than start date.")
        return end
