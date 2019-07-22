from captcha.fields import ReCaptchaField
from crispy_forms.layout import HTML
from django import forms

from extrequests.forms import (
    WorkshopRequestBaseForm,
    WorkshopInquiryRequestBaseForm,
    SelfOrganizedSubmissionBaseForm,
)
from workshops.fields import (
    RadioSelectWithOther,
    CheckboxSelectMultipleWithOthers,
    Select2Widget,
)
from workshops.models import (
    TrainingRequest,
)
from workshops.forms import (
    BootstrapHelper,
)


class TrainingRequestForm(forms.ModelForm):
    # agreement fields are moved to the model

    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True, add_cancel_button=False)

    class Meta:
        model = TrainingRequest
        fields = (
            'group_name',
            'personal',
            'family',
            'email',
            'github',
            'occupation',
            'occupation_other',
            'affiliation',
            'location',
            'country',
            'underresourced',
            'domains',
            'domains_other',
            'underrepresented',
            'underrepresented_details',
            'nonprofit_teaching_experience',
            'previous_involvement',
            'previous_training',
            'previous_training_other',
            'previous_training_explanation',
            'previous_experience',
            'previous_experience_other',
            'previous_experience_explanation',
            'programming_language_usage_frequency',
            'teaching_frequency_expectation',
            'teaching_frequency_expectation_other',
            'max_travelling_frequency',
            'max_travelling_frequency_other',
            'reason',
            'user_notes',
            'data_privacy_agreement',
            'code_of_conduct_agreement',
            'training_completion_agreement',
            'workshop_teaching_agreement',
        )
        widgets = {
            'occupation': RadioSelectWithOther('occupation_other'),
            'domains': CheckboxSelectMultipleWithOthers('domains_other'),
            'gender': forms.RadioSelect(),
            'underrepresented': forms.RadioSelect(),
            'previous_involvement': forms.CheckboxSelectMultiple(),
            'previous_training': RadioSelectWithOther(
                'previous_training_other'),
            'previous_experience': RadioSelectWithOther(
                'previous_experience_other'),
            'programming_language_usage_frequency': forms.RadioSelect(),
            'teaching_frequency_expectation': RadioSelectWithOther(
                'teaching_frequency_expectation_other'),
            'max_travelling_frequency': RadioSelectWithOther(
                'max_travelling_frequency_other'),
            'country': Select2Widget,
        }

    def __init__(self, *args, initial_group_name=None, **kwargs):
        initial = kwargs.pop('initial', {})
        if initial_group_name is not None:
            initial['group_name'] = initial_group_name
        super().__init__(*args, initial=initial, **kwargs)
        if initial_group_name is not None:
            field = self.fields['group_name']
            field.widget = field.hidden_widget()

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up RadioSelectWithOther widget so that it can display additional
        # field inline
        self['occupation'].field.widget.other_field = self['occupation_other']
        self['domains'].field.widget.other_field = self['domains_other']
        self['previous_training'].field.widget.other_field = (
            self['previous_training_other'])
        self['previous_experience'].field.widget.other_field = (
            self['previous_experience_other'])
        self['teaching_frequency_expectation'].field.widget.other_field = (
            self['teaching_frequency_expectation_other'])
        self['max_travelling_frequency'].field.widget.other_field = (
            self['max_travelling_frequency_other'])

        # remove that additional field
        self.helper.layout.fields.remove('occupation_other')
        self.helper.layout.fields.remove('domains_other')
        self.helper.layout.fields.remove('previous_training_other')
        self.helper.layout.fields.remove('previous_experience_other')
        self.helper.layout.fields.remove(
            'teaching_frequency_expectation_other')
        self.helper.layout.fields.remove('max_travelling_frequency_other')

        # add <HR> around "underrepresented*" fields
        index = self.helper.layout.fields.index('underrepresented')
        self.helper.layout.insert(
            index, HTML('<hr class="col-lg-10 col-12 mx-0 px-0">'))

        index = self.helper.layout.fields.index('underrepresented_details')
        self.helper.layout.insert(
            index + 1, HTML('<hr class="col-lg-10 col-12 mx-0 px-0">'))


class WorkshopRequestExternalForm(WorkshopRequestBaseForm):
    captcha = ReCaptchaField()

    class Meta(WorkshopRequestBaseForm.Meta):
        fields = (
            "personal",
            "family",
            "email",
            "institution",
            "institution_other_name",
            "institution_other_URL",
            "institution_department",
            "location",
            "country",
            "requested_workshop_types",
            "preferred_dates",
            "other_preferred_dates",
            "language",
            "number_attendees",
            "audience_description",
            "administrative_fee",
            "scholarship_circumstances",
            "travel_expences_management",
            "travel_expences_management_other",
            "travel_expences_agreement",
            "public_event",
            "public_event_other",
            "institution_restrictions",
            "institution_restrictions_other",
            "additional_contact",
            "carpentries_info_source",
            "carpentries_info_source_other",
            "user_notes",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
            "captcha",
        )


class WorkshopInquiryRequestExternalForm(WorkshopInquiryRequestBaseForm):
    captcha = ReCaptchaField()

    class Meta(WorkshopInquiryRequestBaseForm.Meta):
        fields = (
            "personal",
            "family",
            "email",
            "institution",
            "institution_other_name",
            "institution_other_URL",
            "institution_department",
            "location",
            "country",
            # "your audience" section starts now
            "routine_data",
            "routine_data_other",
            "domains",
            "domains_other",
            "academic_levels",
            "computing_levels",
            "requested_workshop_types",
            "preferred_dates",
            "other_preferred_dates",
            "language",
            "number_attendees",
            "audience_description",
            "administrative_fee",
            "travel_expences_management",
            "travel_expences_management_other",
            "travel_expences_agreement",
            "public_event",
            "public_event_other",
            "institution_restrictions",
            "institution_restrictions_other",
            "additional_contact",
            "carpentries_info_source",
            "carpentries_info_source_other",
            "user_notes",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
            "captcha",
        )


class SelfOrganizedSubmissionExternalForm(SelfOrganizedSubmissionBaseForm):
    captcha = ReCaptchaField()

    class Meta(SelfOrganizedSubmissionBaseForm.Meta):
        fields = (
            "personal",
            "family",
            "email",
            "institution",
            "institution_other_name",
            "institution_other_URL",
            "institution_department",
            "workshop_url",
            "workshop_format",
            "workshop_format_other",
            "workshop_types",
            "workshop_types_other",
            "workshop_types_other_explain",
            "language",
            "public_event",
            "public_event_other",
            "additional_contact",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
            "captcha",
        )
