from crispy_forms.bootstrap import FormActions
from crispy_forms.layout import Layout, Div, HTML, Submit, Field
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, When

from workshops.forms import BootstrapHelper
from workshops.models import (
    Event,
    Person,
    Organization,
    Membership,
    TrainingRequest,
    KnowledgeDomain,
    WorkshopRequest,
    Curriculum,
)
# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import (
    ListSelect2,
    ModelSelect2,
    RadioSelectWithOther,
    CheckboxSelectMultipleWithOthers,
)


class BulkChangeTrainingRequestForm(forms.Form):
    """Form used to bulk discard training requests or bulk unmatch trainees
    from trainings."""

    requests = forms.ModelMultipleChoiceField(
        queryset=TrainingRequest.objects.all())
    # TODO: add training-requests lookup?
    # requests = forms.ModelMultipleChoiceField(
    #     label='Requests',
    #     required=False,
    #     queryset=TrainingRequest.objects.all()
    #     widget=ModelSelect2(url='???-lookup'),
    # )

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False,
                             display_labels=False,
                             add_cancel_button=False)
    helper.layout = Layout(
        # no 'requests' -- you should take care of generating it manually in
        # the template where this form is used

        # We use formnovalidate on submit buttons to disable browser
        # validation. This is necessary because this form is used along with
        # BulkMatchTrainingRequestForm, which have required fields. Both
        # forms live inside the same <form> tag. Without this attribute,
        # when you click one of the following submit buttons, the browser
        # reports missing values in required fields in
        # BulkMatchTrainingRequestForm.
        FormActions(
            Div(
                Submit('discard', 'Discard selected requests',
                       formnovalidate='formnovalidate',
                       css_class="btn-danger"),
                Submit('accept', 'Accept selected requests',
                       formnovalidate='formnovalidate',
                       css_class="btn-success"),
                css_class="btn-group",
            ),
            Submit('unmatch', 'Unmatch selected trainees from training',
                   formnovalidate='formnovalidate'),
            HTML('<a bulk-email-on-click class="btn btn-info text-white">'
                 'Mail selected trainees</a>&nbsp;'),
        )
    )

    # When set to True, the form is valid only if every request is matched to
    # one person. Set to True when 'unmatch' button is clicked, because
    # unmatching makes sense only if each selected TrainingRequest is matched
    # with one person.
    check_person_matched = False

    def clean(self):
        super().clean()
        unmatched_request_exists = any(
            r.person is None for r in self.cleaned_data.get('requests', []))
        if self.check_person_matched and unmatched_request_exists:
            raise ValidationError('Select only requests matched to a person.')


class BulkMatchTrainingRequestForm(forms.Form):
    requests = forms.ModelMultipleChoiceField(
        queryset=TrainingRequest.objects.all())

    event = forms.ModelChoiceField(
        label='Training',
        required=True,
        queryset=Event.objects.filter(tags__name='TTT'),
        widget=ModelSelect2(url='ttt-event-lookup')
    )

    seat_membership = forms.ModelChoiceField(
        label='Membership seats',
        required=False,
        queryset=Membership.objects.all(),
        help_text='Assigned users will take instructor seats from selected '
                  'member site.',
        widget=ModelSelect2(url='membership-lookup'),
    )

    seat_open_training = forms.BooleanField(
        label='Open training seat',
        required=False,
        help_text="Some TTT events allow for open training; check this field "
                  "to count this person into open applications.",
    )

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False,
                             add_cancel_button=False)
    helper.layout = Layout(
        'event', 'seat_membership', 'seat_open_training',
    )
    helper.add_input(
        Submit(
            'match',
            'Accept & match selected trainees to chosen training',
            **{
                'data-toggle': 'popover',
                'data-html': 'true',
                'data-trigger': 'hover',
                'data-content': 'If you want to <strong>re</strong>match '
                                'trainees to other training, first '
                                '<strong>unmatch</strong> them!',
            }
        )
    )

    def clean(self):
        super().clean()

        event = self.cleaned_data['event']
        member_site = self.cleaned_data['seat_membership']
        open_training = self.cleaned_data['seat_open_training']

        if any(
            r.person is None for r in self.cleaned_data.get('requests', [])
        ):
            raise ValidationError('Some of the requests are not matched '
                                  'to a trainee yet. Before matching them to '
                                  'a training, you need to accept them '
                                  'and match with a trainee.')

        if member_site and open_training:
            raise ValidationError(
                "Cannot simultaneously match as open training and use "
                "a Membership instructor training seat."
            )

        if open_training and not event.open_TTT_applications:
            raise ValidationError({
                'seat_open_training': ValidationError(
                    'Selected TTT event does not allow for open training '
                    'seats.'
                ),
            })


class MatchTrainingRequestForm(forms.Form):
    """Form used to match a training request to a Person."""
    person = forms.ModelChoiceField(
        label='Trainee Account',
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2(url='person-lookup'),
    )

    helper = BootstrapHelper(add_submit_button=False,
                             add_cancel_button=False)
    helper.layout = Layout(
        'person',

        FormActions(
            Submit('match-selected-person',
                   'Match to selected trainee account'),
            HTML('&nbsp;<strong>OR</strong>&nbsp;&nbsp;'),
            Submit('create-new-person',
                   'Create new trainee account'),
        )
    )

    def clean(self):
        super().clean()

        if 'match-selected-person' in self.data:
            self.person_required = True
            self.action = 'match'
        elif 'create-new-person' in self.data:
            self.person_required = False
            self.action = 'create'
        else:
            raise ValidationError('Unknown action.')

        if self.person_required and self.cleaned_data['person'] is None:
            raise ValidationError({'person': 'No person was selected.'})

    class Meta:
        fields = [
            'person',
        ]


# ----------------------------------------------------------
# WorkshopRequest related forms

class WorkshopRequestBaseForm(forms.ModelForm):
    institution = forms.ModelChoiceField(
        required=False,
        queryset=Organization.objects.order_by('fullname'),
        widget=ListSelect2(),
        label=WorkshopRequest._meta.get_field('institution').verbose_name,
        help_text=WorkshopRequest._meta.get_field('institution').help_text,
    )
    domains = forms.ModelMultipleChoiceField(
        required=False,
        queryset=KnowledgeDomain.objects.order_by(
            # this crazy django-ninja-code sorts by 'name', but leaves
            # "Don't know yet" entry last
            Case(When(name="Don't know yet", then=-1)), 'name',
        ),
        widget=CheckboxSelectMultipleWithOthers('domains_other'),
        label=WorkshopRequest._meta.get_field('domains').verbose_name,
        help_text=WorkshopRequest._meta.get_field('domains').help_text,
    )

    travel_expences_agreement = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field('travel_expences_agreement')
                                   .verbose_name,
    )
    data_privacy_agreement = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field('data_privacy_agreement')
                                   .verbose_name,
    )
    code_of_conduct_agreement = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field('code_of_conduct_agreement')
                                   .verbose_name,
    )
    host_responsibilities = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field('host_responsibilities')
                                   .verbose_name,
    )

    requested_workshop_types = forms.ModelMultipleChoiceField(
        required=True,
        queryset=Curriculum.objects.order_by(
            # This crazy django-ninja-code gives different weights to entries
            # matching different criterias, and then sorts them by 'name'.
            # For example when two entries (e.g. swc-r and swc-python) have the
            # same weight (here: 5), then sorting by name comes in.
            Case(
                 When(slug="dc-other", then=2),
                 When(slug="lc-other", then=4),
                 When(slug="swc-other", then=6),
                 When(slug="unknown", then=7),
                 When(slug__startswith="dc", then=1),
                 When(slug__startswith="lc", then=3),
                 When(slug__startswith="swc", then=5),
                 default=8,
            ),
            'name',
        ),
        label=WorkshopRequest._meta.get_field('requested_workshop_types')
                                   .verbose_name,
        help_text=WorkshopRequest._meta.get_field('requested_workshop_types')
                                       .help_text,
        widget=forms.CheckboxSelectMultiple(),
    )

    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = WorkshopRequest
        fields = (
            "personal",
            "family",
            "email",
            "institution",
            "institution_name",
            "institution_department",
            "location",
            "country",
            "conference_details",
            "preferred_dates",
            "language",
            "number_attendees",
            "domains",
            "domains_other",
            "academic_levels",
            "computing_levels",
            "audience_description",
            "requested_workshop_types",
            "organization_type",
            "self_organized_github",
            "centrally_organized_fee",
            "waiver_circumstances",
            "travel_expences_management",
            "travel_expences_management_other",
            "travel_expences_agreement",
            "comment",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
        )

        widgets = {
            'country': ListSelect2(),
            'language': ListSelect2(),
            'number_attendees': forms.RadioSelect(),
            'academic_levels': forms.CheckboxSelectMultiple(),
            'computing_levels': forms.CheckboxSelectMultiple(),
            'requested_workshop_types': forms.CheckboxSelectMultiple(),
            'organization_type': forms.RadioSelect(),
            'centrally_organized_fee': forms.RadioSelect(),
            'travel_expences_management':
                RadioSelectWithOther('travel_expences_management_other'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # change institution object labels (originally Organization displays
        # domain as well)
        self.fields['institution'].label_from_instance = \
            self.institution_label_from_instance

        self.fields['travel_expences_management'].required = False

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self['domains'].field.widget.other_field = self['domains_other']
        self['travel_expences_management'].field.widget.other_field = \
            self['travel_expences_management_other']

        # remove additional fields
        self.helper.layout.fields.remove('domains_other')
        self.helper.layout.fields.remove('travel_expences_management_other')

        # get current position of `organization_type` field
        pos_index = self.helper.layout.fields.index('organization_type')

        # setup additional information for the field
        self['organization_type'].field.widget.subfields = {
            'self': [
                self['self_organized_github'],
            ],
            'central': [
                self['centrally_organized_fee'],
                self['waiver_circumstances'],
            ],
        }
        self['organization_type'].field.widget.notes = {
            'self': WorkshopRequest.SELF_ORGANIZED_NOTES,
            'central': WorkshopRequest.CENTRALLY_ORGANIZED_NOTES,
        }
        self.helper.layout.fields.remove('organization_type')
        self.helper.layout.fields.remove('self_organized_github')
        self.helper.layout.fields.remove('centrally_organized_fee')
        self.helper.layout.fields.remove('waiver_circumstances')

        # insert div+field at previously saved position
        self.helper.layout.insert(
            pos_index,
            Div(
                Field('organization_type',
                      template="bootstrap4/layout/radio-accordion.html"),
                css_class='form-group row',
            ),
        )

        # add horizontal lines after some fields to visually group them
        # together
        hr_fields_after = (
            'email', 'institution_department', 'audience_description',
        )
        hr_fields_before = (
            'travel_expences_management',
            'comment',
        )
        for field in hr_fields_after:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field) + 1,
                HTML('<hr class="col-lg-10 col-12 mx-0 px-0">'),
            )
        for field in hr_fields_before:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field),
                HTML('<hr class="col-lg-10 col-12 mx-0 px-0">'),
            )

        # move "institution_name" field to "institution" subfield
        self['institution'].field.widget.subfield = self['institution_name']
        self.helper.layout.fields.remove('institution_name')

    @staticmethod
    def institution_label_from_instance(obj):
        """Static method that overrides ModelChoiceField choice labels,
        essentially works just like `Model.__str__`."""
        return "{}".format(obj.fullname)

    def clean(self):
        super().clean()
        errors = dict()

        # 1: make sure institution is valid
        institution = self.cleaned_data.get('institution', None)
        institution_name = self.cleaned_data.get('institution_name', '')
        if not institution and not institution_name:
            errors['institution'] = ValidationError('Institution is required.')
        elif institution and institution_name:
            errors['institution_name'] = ValidationError(
                "You must select institution, or enter it's name. "
                "You can't do both.")

        # 2: make sure there's institution selected when department is present
        institution_department = self.cleaned_data \
                                     .get('institution_department', '')
        if institution_department and not institution and not institution_name:
            errors['institution_department'] = ValidationError(
                "You must select institution or enter it's name when you "
                "enter department/school details.")

        # 3: * self-organized workshop, require URL
        #    * centrally-organized workshop, require fee description
        #    * fee waiver? require waiver circumstances description
        organization_type = self.cleaned_data.get('organization_type', '')
        self_organized_github = self.cleaned_data \
                                    .get('self_organized_github', '')
        centrally_organized_fee = self.cleaned_data \
                                      .get('centrally_organized_fee', '')
        waiver_circumstances = self.cleaned_data \
                                   .get('waiver_circumstances', '')

        if organization_type == 'self' and not self_organized_github:
            errors['self_organized_github'] = ValidationError(
                "Please enter workshop URL data.")
        elif organization_type == 'central' and not centrally_organized_fee:
            errors['centrally_organized_fee'] = ValidationError(
                "Please select applicable administrative fee option.")
        elif organization_type == 'central' and \
                centrally_organized_fee == 'waiver' and \
                not waiver_circumstances:
            errors['waiver_circumstances'] = ValidationError(
                "Please describe your waiver circumstances.")

        # 5: don't allow empty domains and empty domains_other
        domains = self.cleaned_data.get('domains', '')
        domains_other = self.cleaned_data.get('domains_other', '')
        if not domains and not domains_other:
            errors['domains'] = ValidationError(
                "This field is required. If you're uncertain about what to "
                'choose, select "Don\'t know yet".')

        # 6: don't allow empty travel expences management
        travel_expences_management = \
            self.cleaned_data.get('travel_expences_management', '')
        travel_expences_management_other = \
            self.cleaned_data.get('travel_expences_management_other', '')
        if not travel_expences_management and \
                not travel_expences_management_other:
            errors['travel_expences_management'] = "This field is required."

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


class TrainingRequestUpdateForm(forms.ModelForm):
    person = forms.ModelChoiceField(
        label='Matched Trainee',
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2(url='person-lookup')
    )

    score_auto = forms.IntegerField(
        disabled=True,
        label=TrainingRequest._meta.get_field('score_auto').verbose_name,
        help_text=TrainingRequest._meta.get_field('score_auto').help_text,
    )

    helper = BootstrapHelper(duplicate_buttons_on_top=True,
                             submit_label='Update')

    class Meta:
        model = TrainingRequest
        exclude = ()
        widgets = {
            'occupation': forms.RadioSelect(),
            'domains': forms.CheckboxSelectMultiple(),
            'gender': forms.RadioSelect(),
            'previous_involvement': forms.CheckboxSelectMultiple(),
            'previous_training': forms.RadioSelect(),
            'previous_experience': forms.RadioSelect(),
            'programming_language_usage_frequency': forms.RadioSelect(),
            'teaching_frequency_expectation': forms.RadioSelect(),
            'max_travelling_frequency': forms.RadioSelect(),
            'state': forms.RadioSelect()
        }


class TrainingRequestsSelectionForm(forms.Form):
    trainingrequest_a = forms.ModelChoiceField(
        label='Training request A',
        required=True,
        queryset=TrainingRequest.objects.all(),
        widget=ModelSelect2(url='trainingrequest-lookup')
    )

    trainingrequest_b = forms.ModelChoiceField(
        label='Training request B',
        required=True,
        queryset=TrainingRequest.objects.all(),
        widget=ModelSelect2(url='trainingrequest-lookup')
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class TrainingRequestsMergeForm(forms.Form):
    TWO = (
        ('obj_a', 'Use A'),
        ('obj_b', 'Use B'),
    )
    THREE = TWO + (('combine', 'Combine'), )
    DEFAULT = 'obj_a'

    trainingrequest_a = forms.ModelChoiceField(
        queryset=TrainingRequest.objects.all(), widget=forms.HiddenInput)

    trainingrequest_b = forms.ModelChoiceField(
        queryset=TrainingRequest.objects.all(), widget=forms.HiddenInput)

    id = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    state = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    person = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    group_name = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    personal = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    middle = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    family = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    email = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    github = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    occupation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    occupation_other = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    affiliation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    location = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    country = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    underresourced = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    domains = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    domains_other = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    underrepresented = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    nonprofit_teaching_experience = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    previous_involvement = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    previous_training = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    previous_training_other = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    previous_training_explanation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    previous_experience = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    previous_experience_other = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    previous_experience_explanation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    programming_language_usage_frequency = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    teaching_frequency_expectation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    teaching_frequency_expectation_other = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    max_travelling_frequency = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    max_travelling_frequency_other = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    reason = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    comment = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    training_completion_agreement = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    workshop_teaching_agreement = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    data_privacy_agreement = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    code_of_conduct_agreement = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    created_at = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    last_updated_at = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    notes = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    comments = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )


class WorkshopRequestAdminForm(WorkshopRequestBaseForm):
    helper = BootstrapHelper(add_cancel_button=False,
                             duplicate_buttons_on_top=True)

    class Meta(WorkshopRequestBaseForm.Meta):
        fields = (
            "state",
            "event",
            "personal",
            "family",
            "email",
            "institution",
            "institution_name",
            "institution_department",
            "location",
            "country",
            "conference_details",
            "preferred_dates",
            "language",
            "number_attendees",
            "domains",
            "domains_other",
            "academic_levels",
            "computing_levels",
            "audience_description",
            "requested_workshop_types",
            "organization_type",
            "self_organized_github",
            "centrally_organized_fee",
            "waiver_circumstances",
            "travel_expences_agreement",
            "travel_expences_management",
            "travel_expences_management_other",
            "comment",
            "admin_comment",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
        )

        widgets = WorkshopRequestBaseForm.Meta.widgets.copy()
        widgets.update(
            {'event': ListSelect2()}
        )
