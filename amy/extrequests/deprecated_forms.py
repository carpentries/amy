import re

from django import forms

from extrequests.models import (
    EventRequest,
    EventSubmission,
    DCSelfOrganizedEventRequest,
)
from workshops.forms import (
    BootstrapHelper,
    PrivacyConsentMixin,
)
from workshops.models import (
    Language,
)
from workshops.fields import (
    Select2Widget,
    ModelSelect2Widget,
    RadioSelectWithOther,
    CheckboxSelectMultipleWithOthers,
)


class SWCEventRequestNoCaptchaForm(PrivacyConsentMixin, forms.ModelForm):
    workshop_type = forms.CharField(initial='swc', widget=forms.HiddenInput())
    understand_admin_fee = forms.BooleanField(
        required=True,
        initial=False,
        label='I understand the Software Carpentry Foundation\'s '
              'administration fee.',
        help_text='<a href="http://software-carpentry.org/blog/2015/07/changes'
                  '-to-admin-fee.html" target="_blank">Look up administration '
                  'fees</a>.',
    )
    language = forms.ModelChoiceField(
        label='Language',
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2Widget(data_view='language-lookup')
    )

    helper = BootstrapHelper(wider_labels=True, add_cancel_button=False,
                             duplicate_buttons_on_top=True)

    class Meta:
        model = EventRequest
        exclude = ('created_at', 'last_updated_at', 'assigned_to',
                   'data_types', 'data_types_other',
                   'attendee_data_analysis_level', 'fee_waiver_request', )
        widgets = {
            'event': Select2Widget,
            'approx_attendees': forms.RadioSelect(),
            'attendee_domains': CheckboxSelectMultipleWithOthers(
                'attendee_domains_other'),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_computing_levels': forms.CheckboxSelectMultiple(),
            'travel_reimbursement': RadioSelectWithOther(
                'travel_reimbursement_other'),
            'admin_fee_payment': forms.RadioSelect(),
            'country': Select2Widget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up RadioSelectWithOther widget so that it can display additional
        # field inline
        self['attendee_domains'].field.widget.other_field = \
            self['attendee_domains_other']
        self['travel_reimbursement'].field.widget.other_field = \
            self['travel_reimbursement_other']

        # remove that additional field
        self.helper.layout.fields.remove('attendee_domains_other')
        self.helper.layout.fields.remove('travel_reimbursement_other')


class DCEventRequestNoCaptchaForm(SWCEventRequestNoCaptchaForm):
    workshop_type = forms.CharField(initial='dc', widget=forms.HiddenInput())
    understand_admin_fee = forms.BooleanField(
        required=True,
        initial=False,
        label='I understand the Data Carpentry\'s administration fee.',
        help_text='There is a per-workshop fee for Data Carpentry to cover '
        'administrative and core development costs. The per-workshop fee is '
        'currently $2500. We work to find local instructors when possible, but'
        ' the host institute will also need to pay for instructors travel and'
        ' lodging if they need to travel. Therefore overall workshop costs are'
        ' $2500 - $6000.',
    )

    helper = BootstrapHelper(wider_labels=True, add_cancel_button=False,
                             duplicate_buttons_on_top=True)

    class Meta(SWCEventRequestNoCaptchaForm.Meta):
        exclude = ('created_at', 'last_updated_at', 'assigned_to',
                   'admin_fee_payment', 'attendee_computing_levels', )
        widgets = {
            'event': Select2Widget,
            'approx_attendees': forms.RadioSelect(),
            'attendee_domains': CheckboxSelectMultipleWithOthers(
                'attendee_domains_other'),
            'data_types': RadioSelectWithOther('data_types_other'),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_data_analysis_level': forms.CheckboxSelectMultiple(),
            'travel_reimbursement': RadioSelectWithOther(
                'travel_reimbursement_other'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up RadioSelectWithOther widget so that it can display additional
        # field inline
        self['attendee_domains'].field.widget.other_field = \
            self['attendee_domains_other']
        self['data_types'].field.widget.other_field = \
            self['data_types_other']
        self['travel_reimbursement'].field.widget.other_field = \
            self['travel_reimbursement_other']

        # remove that additional field
        self.helper.layout.fields.remove('attendee_domains_other')
        self.helper.layout.fields.remove('data_types_other')
        self.helper.layout.fields.remove('travel_reimbursement_other')


class EventSubmitFormNoCaptcha(forms.ModelForm):
    class Meta:
        model = EventSubmission
        exclude = ('created_at', 'last_updated_at', 'assigned_to', )
        widgets = {
            'event': Select2Widget,
        }


class DCSelfOrganizedEventRequestFormNoCaptcha(forms.ModelForm):
    # the easiest way to make these fields required without rewriting their
    # verbose names or help texts
    handle_registration = DCSelfOrganizedEventRequest._meta \
        .get_field('handle_registration').formfield(required=True)
    distribute_surveys = DCSelfOrganizedEventRequest._meta \
        .get_field('distribute_surveys').formfield(required=True)
    follow_code_of_conduct = DCSelfOrganizedEventRequest._meta \
        .get_field('follow_code_of_conduct').formfield(required=True)

    class Meta:
        model = DCSelfOrganizedEventRequest
        exclude = ('created_at', 'last_updated_at', 'assigned_to')
        widgets = {
            'event': Select2Widget,
            'instructor_status': forms.RadioSelect(),
            'is_partner': forms.RadioSelect(),
            'domains': forms.CheckboxSelectMultiple(),
            'topics': forms.CheckboxSelectMultiple(),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_data_analysis_level': forms.CheckboxSelectMultiple(),
            'payment': forms.RadioSelect(),
        }
