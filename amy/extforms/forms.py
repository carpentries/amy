from captcha.fields import ReCaptchaField
from crispy_forms.layout import HTML, Div, Field
from django import forms
from django.core.exceptions import ValidationError

from extrequests.forms import (
    WorkshopRequestBaseForm,
    WorkshopInquiryRequestBaseForm,
    SelfOrganisedSubmissionBaseForm,
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
            'review_process',
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
            'review_process': forms.RadioSelect(),
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
            initial['review_process'] = 'preapproved'
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

        # fake requiredness of the registration code / group name
        self['group_name'].field.widget.fake_required = True

        # special accordion display for the review process
        self['review_process'].field.widget.subfields = {
            'preapproved': [
                self['group_name'],
            ],
            'open': [],  # this option doesn't require any additional fields
        }
        self['review_process'].field.widget.notes = \
            TrainingRequest.REVIEW_CHOICES_NOTES

        # get current position of `review_process` field
        pos_index = self.helper.layout.fields.index('review_process')

        self.helper.layout.fields.remove('review_process')
        self.helper.layout.fields.remove('group_name')

        # insert div+field at previously saved position
        self.helper.layout.insert(
            pos_index,
            Div(
                Field('review_process',
                      template="bootstrap4/layout/radio-accordion.html"),
                css_class='form-group row',
            ),
        )

        # add <HR> around "underrepresented*" fields
        index = self.helper.layout.fields.index('underrepresented')
        self.helper.layout.insert(
            index, HTML(self.helper.hr()))

        index = self.helper.layout.fields.index('underrepresented_details')
        self.helper.layout.insert(
            index + 1, HTML(self.helper.hr()))

    def clean(self):
        super().clean()
        errors = dict()

        # 1: validate registration code / group name
        review_process = self.cleaned_data.get('review_process', '')
        group_name = self.cleaned_data.get('group_name', '').split()

        # it's required when review_process is 'preapproved', but not when
        # 'open'
        if review_process == 'preapproved' and not group_name:
            errors['review_process'] = ValidationError(
                "Registration code is required for pre-approved training "
                "review process."
            )

        # it's required to be empty when review_process is 'open'
        if review_process == 'open' and group_name:
            errors['review_process'] = ValidationError(
                "Registration code must be empty for open training review "
                "process."
            )

        if errors:
            raise ValidationError(errors)


class WorkshopRequestExternalForm(WorkshopRequestBaseForm):
    captcha = ReCaptchaField()

    class Meta(WorkshopRequestBaseForm.Meta):
        fields = WorkshopRequestBaseForm.Meta.fields + ("captcha", )


class WorkshopInquiryRequestExternalForm(WorkshopInquiryRequestBaseForm):
    captcha = ReCaptchaField()

    class Meta(WorkshopInquiryRequestBaseForm.Meta):
        fields = WorkshopInquiryRequestBaseForm.Meta.fields + ("captcha", )


class SelfOrganisedSubmissionExternalForm(SelfOrganisedSubmissionBaseForm):
    captcha = ReCaptchaField()

    class Meta(SelfOrganisedSubmissionBaseForm.Meta):
        fields = SelfOrganisedSubmissionBaseForm.Meta.fields + ("captcha", )
