from collections import defaultdict
from datetime import date
from typing import Any, Optional, Union

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q, QuerySet

from workshops.fields import HeavySelect2Widget, ModelSelect2Widget
from workshops.forms import SELECT2_SIDEBAR, BootstrapHelper, WidgetOverrideMixin
from workshops.models import Award, Person

from .fields import CustomKeysJSONField
from .models import CommunityRole, CommunityRoleConfig, CommunityRoleInactivation


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
            "config": HeavySelect2Widget(data_view="api-v1:communityroleconfig-list", attrs=SELECT2_SIDEBAR),
            "person": ModelSelect2Widget(data_view="person-lookup", attrs=SELECT2_SIDEBAR),
            "award": ModelSelect2Widget(data_view="award-lookup", attrs=SELECT2_SIDEBAR),
            "membership": ModelSelect2Widget(data_view="membership-lookup", attrs=SELECT2_SIDEBAR),
            "generic_relation_content_type": forms.Select(
                # "disabled" means the browsers will not send the field during POST.
                # See how it's handled in `clean()` method below.
                attrs={"disabled": ""},
            ),
            "generic_relation_pk": HeavySelect2Widget(data_view="generic-object-lookup", attrs=SELECT2_SIDEBAR),
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

    def clean(self) -> Union[dict[str, Any], None]:
        """Validate form according to rules set up in related Community Role
        configuration."""
        cleaned_data = super().clean()
        if not cleaned_data:
            return cleaned_data

        errors: defaultdict[str, list[ValidationError]] = defaultdict(list)
        config: Optional[CommunityRoleConfig] = cleaned_data.get("config")
        award: Optional[Award] = cleaned_data.get("award")
        person: Optional[Person] = cleaned_data.get("person")
        inactivation: Optional[CommunityRoleInactivation] = cleaned_data.get("inactivation")
        start_date: Optional[date] = cleaned_data.get("start")
        end_date: Optional[date] = cleaned_data.get("end")
        url: Optional[str] = cleaned_data.get("url")

        # Config is required, but field validation for 'config' should raise
        # validation error first.
        if not config or not person:
            return cleaned_data

        # Award required?
        if config.link_to_award and not award:
            errors["award"].append(ValidationError(f"Award is required with community role {config}"))

        # Award should point at the same person the community role links to
        if award and award.person != person:
            errors["award"].append(ValidationError(f"Award should belong to {person}"))

        # Specific award badge required?
        if (badge := config.award_badge_limit) and award:
            if award.badge != badge:
                errors["award"].append(ValidationError(f"Award badge must be {badge} for community role {config}"))

        # Membership required?
        if config.link_to_membership and not cleaned_data.get("membership"):
            errors["membership"].append(ValidationError(f"Membership is required with community role {config}"))

        # Additional URL supported and required?
        if config.additional_url and not url:
            errors["url"].append(ValidationError(f"URL is required for community role {config}"))

        # Generic relation object must exist
        if config.generic_relation_content_type and cleaned_data.get("generic_relation_pk"):
            model_class = config.generic_relation_content_type.model_class()
            try:
                model_class._base_manager.get(pk=cleaned_data.get("generic_relation_pk"))
            except ObjectDoesNotExist:
                errors["generic_relation_pk"].append(
                    ValidationError(f"Generic relation object of model {model_class.__name__} " "doesn't exist")
                )

        # End date is required when any inactivation was selected.
        if inactivation is not None and end_date is None:
            errors["end"].append(ValidationError("Required when Reason for inactivation selected."))

        # Person should not have any concurrent Community Roles of the same type in the
        # same time.
        if concurrent_roles := self.find_concurrent_roles(config, person, start_date, end_date, url):
            errors["person"].append(
                ValidationError(f"Person {person} has concurrent community roles: " f"{list(concurrent_roles)}.")
            )

        if errors:
            raise ValidationError(errors)  # type: ignore

        return cleaned_data

    def clean_end(self):
        """Validate that end >= start"""
        start = self.cleaned_data.get("start")
        end = self.cleaned_data.get("end")
        if start and end and end < start:
            raise ValidationError("Must not be earlier than start date.")
        return end

    def clean_generic_relation_content_type(self) -> Optional[ContentType]:
        """Copy content type from the Community Role Configuration."""

        # Widget for `generic_relation_content_type` is disabled in HTML, which
        # makes browsers not send it. The code below sets the default value to
        # the same value as in related config.
        config: Optional[CommunityRoleConfig] = self.cleaned_data.get("config")
        if config:
            return config.generic_relation_content_type
        return None

    @staticmethod
    def find_concurrent_roles(
        config: Optional[CommunityRoleConfig] = None,
        person: Optional[Person] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        url: Optional[str] = None,
    ) -> Optional[QuerySet[CommunityRole]]:
        """Lookup concurrent Community Roles."""
        # These are required fields in the form, so they should be present.
        if config and person and start_date:
            initial_conditions = Q(end__gt=start_date) | Q(end__isnull=True)

            # if `end_date` is present, introduce additional condition
            if end_date:
                initial_conditions &= Q(start__lt=end_date) | Q(start__isnull=True)

            # if configuration requires URL, add URL to conditions
            if config.additional_url:
                initial_conditions &= Q(url=url)

            roles = CommunityRole.objects.filter(initial_conditions, person=person, config=config)
            return roles
        return None


class CommunityRoleUpdateForm(CommunityRoleForm):
    config = forms.ModelChoiceField(
        queryset=CommunityRoleConfig.objects.all(),
        disabled=True,
    )

    custom_keys = CustomKeysJSONField(required=False)

    class Meta(CommunityRoleForm.Meta):
        fields = CommunityRoleForm.Meta.fields + ("custom_keys",)

    def __init__(self, *args, community_role_config: CommunityRoleConfig, **kwargs):
        self.config = community_role_config
        super().__init__(*args, **kwargs)
        self.fields["custom_keys"].apply_labels(self.config.custom_key_labels)  # type: ignore

    @staticmethod
    def find_concurrent_roles(
        config: Optional[CommunityRoleConfig] = None,
        person: Optional[Person] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        url: Optional[str] = None,
    ) -> Optional[QuerySet[CommunityRole]]:
        """When updating a CommunityRole, we shouldn't check for concurrent roles."""
        return None
