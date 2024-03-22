from typing import Iterable, cast

from captcha.fields import ReCaptchaField
from crispy_forms.layout import HTML, Div, Field, Layout
from django import forms
from django.core.exceptions import ValidationError
from django.db.models.fields import BLANK_CHOICE_DASH

from consents.forms import option_display_value
from consents.models import Term, TrainingRequestConsent
from extrequests.forms import (
    SelfOrganisedSubmissionBaseForm,
    WorkshopInquiryRequestBaseForm,
    WorkshopRequestBaseForm,
)
from workshops.fields import (
    CheckboxSelectMultipleWithOthers,
    RadioSelectWithOther,
    Select2Widget,
)
from workshops.forms import BootstrapHelper
from workshops.models import TrainingRequest


class TrainingRequestForm(forms.ModelForm):
    # agreement fields are moved to the model

    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True, add_cancel_button=False)

    class Meta:
        model = TrainingRequest
        fields = (
            "personal",
            "family",
            "group_name",
            "email",
            "secondary_email",
            "github",
            "occupation",
            "occupation_other",
            "affiliation",
            "location",
            "country",
            "underresourced",
            "domains",
            "domains_other",
            "underrepresented",
            "underrepresented_details",
            "nonprofit_teaching_experience",
            "previous_involvement",
            "previous_training",
            "previous_training_other",
            "previous_training_explanation",
            "previous_experience",
            "previous_experience_other",
            "previous_experience_explanation",
            "programming_language_usage_frequency",
            "teaching_frequency_expectation",
            "teaching_frequency_expectation_other",
            "max_travelling_frequency",
            "max_travelling_frequency_other",
            "reason",
            "user_notes",
            # "data_privacy_agreement",
            "code_of_conduct_agreement",
            "training_completion_agreement",
            "workshop_teaching_agreement",
        )
        widgets = {
            "occupation": RadioSelectWithOther("occupation_other"),
            "domains": CheckboxSelectMultipleWithOthers("domains_other"),
            "underrepresented": forms.RadioSelect(),
            "previous_involvement": forms.CheckboxSelectMultiple(),
            "previous_training": RadioSelectWithOther("previous_training_other"),
            "previous_experience": RadioSelectWithOther("previous_experience_other"),
            "programming_language_usage_frequency": forms.RadioSelect(),
            "teaching_frequency_expectation": RadioSelectWithOther(
                "teaching_frequency_expectation_other"
            ),
            "max_travelling_frequency": RadioSelectWithOther(
                "max_travelling_frequency_other"
            ),
            "country": Select2Widget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only active and required terms.
        self.terms = (
            Term.objects.prefetch_active_options()
            .filter(required_type=Term.PROFILE_REQUIRE_TYPE)
            .order_by("slug")
        )

        self.set_consent_fields(self.terms)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        self.set_other_fields(self.helper.layout)
        self.set_fake_required_fields()
        self.set_hr(self.helper.layout)

    def set_other_field(self, field_name: str, layout: Layout) -> None:
        """
        Set up a field so that it can be displayed as a separate widget.
        """
        WidgetType = self._meta.widgets[field_name].__class__  # type: ignore
        cast(WidgetType, self[field_name].field.widget).other_field = self[
            f"{field_name}_other"
        ]
        layout.fields.remove(f"{field_name}_other")

    def set_other_fields(self, layout: Layout) -> None:
        """
        Set fields that have "Other" counterpart as a separate widget.
        """
        # Set up "*WithOther" widgets so that they can display additional
        # inline fields. The original "*other" fields are removed from the layout.
        self.set_other_field("occupation", layout)
        self.set_other_field("domains", layout)
        self.set_other_field("previous_training", layout)
        self.set_other_field("previous_experience", layout)
        self.set_other_field("teaching_frequency_expectation", layout)
        self.set_other_field("max_travelling_frequency", layout)

    def set_fake_required_fields(self) -> None:
        # fake requiredness of the registration code / group name
        self["group_name"].field.widget.fake_required = True  # type: ignore

    def set_accordion(self, layout: Layout) -> None:
        # Note: not used since 2024-03-19 (#2617).

        # special accordion display for the review process
        self["review_process"].field.widget.subfields = {  # type: ignore
            "preapproved": [
                self["group_name"],
            ],
            "open": [],  # this option doesn't require any additional fields
        }
        self[
            "review_process"
        ].field.widget.notes = TrainingRequest.REVIEW_CHOICES_NOTES  # type: ignore

        # get current position of `review_process` field
        pos_index = layout.fields.index("review_process")

        layout.fields.remove("review_process")
        layout.fields.remove("group_name")

        # insert div+field at previously saved position
        layout.insert(
            pos_index,
            Div(
                Field(
                    "review_process", template="bootstrap4/layout/radio-accordion.html"
                ),
                css_class="form-group row",
            ),
        )

    def set_hr(self, layout: Layout) -> None:
        # add <HR> around "underrepresented*" fields
        index = layout.fields.index("underrepresented")
        layout.insert(index, HTML(self.helper.hr()))

        index = layout.fields.index("underrepresented_details")
        layout.insert(index + 1, HTML(self.helper.hr()))

    def set_consent_fields(self, terms: Iterable[Term]) -> None:
        for term in terms:
            self.fields[term.slug] = self.create_consent_field(term)

    def create_consent_field(self, term: Term) -> forms.ChoiceField:
        options = [(opt.pk, option_display_value(opt)) for opt in term.options]
        label = term.training_request_content or term.content
        required = term.required_type == Term.PROFILE_REQUIRE_TYPE
        initial = None
        attrs = {"class": "border border-warning"} if initial is None else {}

        field = forms.ChoiceField(
            choices=BLANK_CHOICE_DASH + options,
            label=label,
            required=required,
            initial=initial,
            help_text=term.help_text or "",
            widget=forms.Select(attrs=attrs),
        )
        return field

    def clean(self):
        super().clean()
        errors = dict()

        # Since 2024-03-19 (#2617) we don't allow open training applications. All
        # applications are by default pre-approved.
        review_process = self.cleaned_data.get("review_process", "preapproved")
        self.instance.review_process = review_process

        # 1: validate registration code / group name
        group_name = self.cleaned_data.get("group_name", "").split()

        # it's required when review_process is 'preapproved', but not when
        # 'open'
        if review_process == "preapproved" and not group_name:
            errors["group_name"] = ValidationError(
                "Registration code is required for pre-approved training "
                "review process."
            )

        # it's required to be empty when review_process is 'open'
        if review_process == "open" and group_name:
            errors["member_code"] = ValidationError(
                "Registration code must be empty for open training review process."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs) -> None:
        training_request = super().save(*args, **kwargs)
        new_consents: list[TrainingRequestConsent] = []
        for term in self.terms:
            option_id = self.cleaned_data.get(term.slug)
            if not option_id:
                continue
            new_consents.append(
                TrainingRequestConsent(
                    training_request=training_request,
                    term_option_id=option_id,
                    term_id=term.pk,
                )
            )
        TrainingRequestConsent.objects.bulk_create(new_consents)
        return training_request


class WorkshopRequestExternalForm(WorkshopRequestBaseForm):
    captcha = ReCaptchaField()

    class Meta(WorkshopRequestBaseForm.Meta):
        fields = WorkshopRequestBaseForm.Meta.fields + ("captcha",)


class WorkshopInquiryRequestExternalForm(WorkshopInquiryRequestBaseForm):
    captcha = ReCaptchaField()

    class Meta(WorkshopInquiryRequestBaseForm.Meta):
        fields = WorkshopInquiryRequestBaseForm.Meta.fields + ("captcha",)


class SelfOrganisedSubmissionExternalForm(SelfOrganisedSubmissionBaseForm):
    captcha = ReCaptchaField()

    class Meta(SelfOrganisedSubmissionBaseForm.Meta):
        fields = SelfOrganisedSubmissionBaseForm.Meta.fields + ("captcha",)
