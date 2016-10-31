import re

from captcha.fields import ReCaptchaField
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Submit, Button, Field
from crispy_forms.bootstrap import AccordionGroup, Accordion
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import (
    HiddenInput, CheckboxSelectMultiple, TextInput, modelformset_factory,
    RadioSelect,
    URLField,
)
from django_countries import Countries
from django_countries.fields import CountryField
from selectable import forms as selectable

from workshops import lookups
from workshops.models import (
    Award, Event, Lesson, Person, Task, Airport, Organization,
    EventRequest, ProfileUpdateRequest, TodoItem, Membership,
    Sponsorship, InvoiceRequest, EventSubmission,
    TrainingRequest,
    DCSelfOrganizedEventRequest,
    TrainingProgress,
)

class BootstrapHelper(FormHelper):
    """Layout and behavior for crispy-displayed forms."""
    html5_required = True

    def __init__(self,
                 form=None,
                 duplicate_buttons_on_top=False,
                 submit_label='Submit',
                 submit_name='submit',
                 use_get_method=False,
                 wider_labels=False,
                 add_submit_button=True,
                 add_delete_button=False,
                 add_cancel_button=True,
                 additional_form_class='',
                 form_tag=True,
                 display_labels=True,
                 form_action=None,
                 form_id=None):
        """
        `duplicate_buttons_on_top` -- Whether submit buttons should be
        displayed on both top and bottom of the form.

        `use_get_method` -- Force form to use GET instead of default POST.

        `wider_labels` -- SWCEventRequestForm and DCEventRequestForm have
        long labels, so this flag (set to True) is used to address that issue.

        `add_delete_button` -- displays additional red "delete" button.
        If you want to use it, you need to include in your template the
        following code:

            <form action="delete?next={{ request.GET.next|urlencode }}" method="POST" id="delete-form">
              {% csrf_token %}
            </form>

        This is necessary, because delete button must be reassigned from the
        form using this helper to "delete-form". This reassignment is done
        via HTML5 "form" attribute on the "delete" button.

        `display_labels` -- Set to False, when your form has only submit
        buttons and you want these buttons to be aligned to left.
        """

        super().__init__(form)

        self.attrs['role'] = 'form'

        self.duplicate_buttons_on_top = duplicate_buttons_on_top

        self.submit_label = submit_label

        if use_get_method:
            self.form_method = 'get'

        if wider_labels:
            assert display_labels
            self.label_class = 'col-lg-3'
            self.field_class = 'col-lg-7'
        elif display_labels:
            self.label_class = 'col-lg-2'
            self.field_class = 'col-lg-8'
        else:
            self.label_class = ''
            self.field_class = 'col-lg-12'

        if add_submit_button:
            self.add_input(Submit(submit_name, submit_label))

        if add_delete_button:
            self.add_input(Submit(
                'delete', 'Delete',
                onclick='return confirm("Are you sure you want to delete it?");',
                form='delete-form',
                css_class='btn-danger',
                style='float: right;'))

        if add_cancel_button:
            self.add_input(Button(
                'cancel', 'Cancel',
                css_class='btn-default pull-right',
                onclick='window.history.back()'))

        self.form_class = 'form-horizontal ' + additional_form_class

        self.form_tag = form_tag

        if form_action is not None:
            self.form_action = form_action

        if form_id is not None:
            self.form_id = form_id



class BootstrapHelperFilter(FormHelper):
    """A differently shaped forms (more space-efficient) for use in sidebar as
    filter forms."""
    form_method = 'get'
    form_id = 'filter-form'

    def __init__(self, form=None):
        super().__init__(form)
        self.attrs['role'] = 'form'
        self.inputs.append(Submit('', 'Submit'))


class BootstrapHelperFormsetInline(BootstrapHelper):
    """For use in inline formsets."""
    template = 'bootstrap/table_inline_formset.html'


bootstrap_helper = BootstrapHelper()
bootstrap_helper_filter = BootstrapHelperFilter()
bootstrap_helper_inline_formsets = BootstrapHelperFormsetInline()


class PrivacyConsentMixin(forms.Form):
    privacy_consent = forms.BooleanField(
        label='*I have read and agree to <a href='
              '"https://software-carpentry.org/privacy/" target="_blank">'
              'the Software Carpentry Foundation\'s data privacy policy</a>.',
        required=True)


class WorkshopStaffForm(forms.Form):
    '''Represent instructor matching form.'''

    latitude = forms.FloatField(label='Latitude',
                                min_value=-90.0,
                                max_value=90.0,
                                required=False)
    longitude = forms.FloatField(label='Longitude',
                                 min_value=-180.0,
                                 max_value=180.0,
                                 required=False)
    airport = selectable.AutoCompleteSelectField(
        lookup_class=lookups.AirportLookup,
        label='Airport',
        required=False,
        widget=selectable.AutoComboboxSelectWidget(
            lookup_class=lookups.AirportLookup,
        ),
    )
    languages = selectable.AutoCompleteSelectMultipleField(
        lookup_class=lookups.LanguageLookup,
        label='Languages',
        required=False,
        widget=selectable.AutoComboboxSelectMultipleWidget,
    )

    country = forms.MultipleChoiceField(choices=[])

    lessons = forms.ModelMultipleChoiceField(queryset=Lesson.objects.all(),
                                             widget=CheckboxSelectMultiple(),
                                             required=False)

    INSTRUCTOR_BADGE_CHOICES = (
        ('swc-instructor', 'Software Carpentry Instructor'),
        ('dc-instructor', 'Data Carpentry Instructor'),
    )
    instructor_badges = forms.MultipleChoiceField(
        choices=INSTRUCTOR_BADGE_CHOICES,
        widget=CheckboxSelectMultiple(),
        required=False,
    )

    GENDER_CHOICES = ((None, '---------'), ) + Person.GENDER_CHOICES
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)

    was_helper = forms.BooleanField(
        required=False, label='Was helper at least once before')
    was_organizer = forms.BooleanField(
        required=False, label='Was organizer at least once before')
    is_in_progress_trainee = forms.BooleanField(
        required=False, label='Is an in-progress instructor trainee')

    def __init__(self, *args, **kwargs):
        '''Build form layout dynamically.'''
        super().__init__(*args, **kwargs)

        # dynamically build choices for country field
        only = Airport.objects.distinct().exclude(country='') \
                                         .exclude(country=None) \
                                         .values_list('country', flat=True)
        countries = Countries()
        countries.only = only

        choices = list(countries)
        self.fields['country'] = forms.MultipleChoiceField(choices=choices,
                                                           required=False)

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Div(
                Div(HTML('Location close to'), css_class='panel-heading'),
                Div('airport', css_class='panel-body'),
                Div(HTML('<b>OR</b>'), css_class='panel-footer'),
                Div('country', css_class='panel-body'),
                Div(HTML('<b>OR</b>'), css_class='panel-footer'),
                Div('latitude', 'longitude', css_class='panel-body'),
                css_class='panel panel-default ',
            ),
            'instructor_badges',
            'was_helper',
            'was_organizer',
            'is_in_progress_trainee',
            'languages',
            'gender',
            'lessons',
            FormActions(
                Submit('submit', 'Submit'),
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        lat = bool(cleaned_data.get('latitude'))
        lng = bool(cleaned_data.get('longitude'))
        airport = bool(cleaned_data.get('airport'))
        country = bool(cleaned_data.get('country'))
        latlng = lat and lng

        # if searching by coordinates, then there must be both lat & lng
        # present
        if lat ^ lng:
            raise forms.ValidationError(
                'Must specify both latitude and longitude if searching by '
                'coordinates')

        # User must search by airport, or country, or coordinates, or none
        # of them. Sum of boolean elements must be equal 0 (if general search)
        # or 1 (if searching by airport OR country OR lat/lng).
        if sum([airport, country, latlng]) not in [0, 1]:
            raise forms.ValidationError(
                'Must specify an airport OR a country, OR use coordinates, OR '
                'none of them.')
        return cleaned_data


class PersonBulkAddForm(forms.Form):
    '''Represent CSV upload form for bulk adding people.'''

    file = forms.FileField()


class SearchForm(forms.Form):
    '''Represent general searching form.'''

    term = forms.CharField(label='term',
                           max_length=100)
    in_organizations = forms.BooleanField(label='in organizations',
                                  required=False,
                                  initial=True)
    in_events = forms.BooleanField(label='in events',
                                   required=False,
                                   initial=True)
    in_persons = forms.BooleanField(label='in persons',
                                    required=False,
                                    initial=True)
    in_airports = forms.BooleanField(label='in airports',
                                     required=False,
                                     initial=True)
    in_training_requests = forms.BooleanField(label='in training requests',
                                              required=False,
                                              initial=True)

    helper = BootstrapHelper(add_cancel_button=False)


class DebriefForm(forms.Form):
    '''Represent general debrief form.'''
    begin_date = forms.DateField(
        label='Begin date as YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ]
    )
    end_date = forms.DateField(
        label='End date as YYYY-MD-DD',
        input_formats=['%Y-%m-%d', ]
    )

    helper = BootstrapHelper(use_get_method=True)


class EventForm(forms.ModelForm):
    host = selectable.AutoCompleteSelectField(
        lookup_class=lookups.OrganizationLookup,
        label='Host',
        required=True,
        help_text=Event._meta.get_field('host').help_text,
        widget=selectable.AutoComboboxSelectWidget,
    )

    administrator = selectable.AutoCompleteSelectField(
        lookup_class=lookups.OrganizationLookup,
        label='Administrator',
        required=False,
        help_text=Event._meta.get_field('administrator').help_text,
        widget=selectable.AutoComboboxSelectWidget,
    )

    assigned_to = selectable.AutoCompleteSelectField(
        lookup_class=lookups.AdminLookup,
        label='Assigned to',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    language = selectable.AutoCompleteSelectField(
        lookup_class=lookups.LanguageLookup,
        label='Language',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    country = CountryField().formfield(
        required=False,
        help_text=Event._meta.get_field('country').help_text,
    )

    admin_fee = forms.DecimalField(min_value=0, decimal_places=2,
                                   required=False, widget=TextInput)

    helper = BootstrapHelper()
    helper.layout = Layout(
        Field('slug', placeholder='YYYY-MM-DD-location'),
        'completed',
        Field('start', placeholder='YYYY-MM-DD'),
        Field('end', placeholder='YYYY-MM-DD'),
        'host',
        'administrator',
        'assigned_to',
        'tags',
        'url',
        'language',
        'reg_key',
        'admin_fee',
        'invoice_status',
        'attendance',
        'contact',
        'notes',
        Accordion(
            AccordionGroup('Location details',
                'country',
                'venue',
                'address',
                'latitude',
                'longitude',
            ),
        ),
    )

    def clean_slug(self):
        # Ensure slug is in "YYYY-MM-DD-location" format
        data = self.cleaned_data['slug']
        match = re.match('(\d{4}|x{4})-(\d{2}|x{2})-(\d{2}|x{2})-.+', data)
        if not match:
            raise forms.ValidationError('Slug must be in "YYYY-MM-DD-location"'
                                        ' format, where "YYYY", "MM", "DD" can'
                                        ' be unspecified (ie. "xx").')
        return data

    def clean_end(self):
        """Ensure end >= start."""
        start = self.cleaned_data['start']
        end = self.cleaned_data['end']

        if start and end and end < start:
            raise forms.ValidationError('Must not be earlier than start date.')
        return end

    class Meta:
        model = Event
        fields = ('slug', 'completed', 'start', 'end', 'host', 'administrator',
                  'assigned_to', 'tags', 'url', 'language', 'reg_key', 'venue',
                  'admin_fee', 'invoice_status', 'attendance', 'contact',
                  'notes', 'country', 'address', 'latitude', 'longitude', )
        widgets = {
            'attendance': TextInput,
            'latitude': TextInput,
            'longitude': TextInput,
            'invoice_status': RadioSelect,
        }

    class Media:
        # thanks to this, {{ form.media }} in the template will generate
        # a <link href=""> (for CSS files) or <script src=""> (for JS files)
        js = (
            'date_yyyymmdd.js',
            'import_from_url.js', 'update_from_url.js',
            'online_country.js',
        )


class TaskForm(forms.ModelForm):

    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(submit_label='Add')

    class Meta:
        model = Task
        fields = '__all__'
        widgets = {'event': HiddenInput}


class TaskFullForm(TaskForm):

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    class Meta:
        model = Task
        fields = '__all__'


class PersonForm(forms.ModelForm):

    airport = selectable.AutoCompleteSelectField(
        lookup_class=lookups.AirportLookup,
        label='Airport',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )
    languages = selectable.AutoCompleteSelectMultipleField(
        lookup_class=lookups.LanguageLookup,
        label='Languages',
        required=False,
        widget=selectable.AutoComboboxSelectMultipleWidget,
    )

    helper = BootstrapHelper(form_id='person-edit-form')

    class Meta:
        model = Person
        # don't display the 'password', 'user_permissions',
        # 'groups' or 'is_superuser' fields
        # + reorder fields
        fields = ['username', 'personal', 'middle', 'family', 'may_contact',
                  'email', 'gender', 'airport', 'affiliation', 'github',
                  'twitter', 'url', 'occupation', 'orcid', 'notes', 'lessons',
                  'domains', 'languages']


class PersonCreateForm(PersonForm):
    class Meta(PersonForm.Meta):
        # remove 'username' field as it's being populated after form save
        # in the `views.PersonCreate.form_valid`
        fields = PersonForm.Meta.fields.copy()
        fields.remove('username')


class PersonPermissionsForm(forms.ModelForm):
    class Meta:
        model = Person
        # only display administration-related fields: groups, permissions,
        # being a superuser or being active (== ability to log in)
        fields = [
            'is_active',
            'is_superuser',
            'user_permissions',
            'groups',
        ]


class PersonsSelectionForm(forms.Form):

    person_a = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person From',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    person_b = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person To',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(use_get_method=True)


class PersonsMergeForm(forms.Form):
    TWO = (
        ('obj_a', 'Use A'),
        ('obj_b', 'Use B'),
    )
    THREE = TWO + (('combine', 'Combine'), )
    DEFAULT = 'obj_a'

    person_a = forms.ModelChoiceField(queryset=Person.objects.all(),
                                      widget=forms.HiddenInput)

    person_b = forms.ModelChoiceField(queryset=Person.objects.all(),
                                      widget=forms.HiddenInput)

    id = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    username = forms.ChoiceField(
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
    may_contact = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    gender = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    airport = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    github = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    twitter = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    url = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    notes = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    affiliation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    occupation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    orcid = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    award_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    qualification_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
        label='Lessons',
    )
    domains = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    languages = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    task_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    is_active = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )


class BadgeAwardForm(forms.ModelForm):

    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    awarded_by = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Awarded by',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = bootstrap_helper

    class Meta:
        model = Award
        fields = '__all__'
        widgets = {'badge': HiddenInput}


class PersonAwardForm(forms.ModelForm):

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    awarded_by = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Awarded by',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(submit_label='Add', form_id='person-awards-form')

    class Meta:
        model = Award
        fields = '__all__'
        widgets = {'person': HiddenInput}


class PersonTaskForm(forms.ModelForm):

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(submit_label='Add', form_id='person-tasks-form')

    class Meta:
        model = Task
        fields = '__all__'
        widgets = {'person': HiddenInput}


class OrganizationForm(forms.ModelForm):
    domain = forms.CharField(
        max_length=Organization._meta.get_field('domain').max_length,
        validators=[
            RegexValidator(
                '[^\w\.-]+', inverse_match=True,
                message='Please enter only the domain (such as "math.esu.edu")'
                        ' without a leading "http://" or a trailing "/".')
        ],
    )

    helper = bootstrap_helper

    class Meta:
        model = Organization
        fields = ['domain', 'fullname', 'country', 'notes']


class MembershipForm(forms.ModelForm):
    organization = selectable.AutoCompleteSelectField(
        lookup_class=lookups.OrganizationLookup,
        label='Organization',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = bootstrap_helper

    class Meta:
        model = Membership
        fields = '__all__'
        widgets = {'host': HiddenInput, }


class SponsorshipForm(forms.ModelForm):

    organization = selectable.AutoCompleteSelectField(
        lookup_class=lookups.OrganizationLookup,
        label='Organization',
        required=True,
        help_text=Sponsorship._meta.get_field('organization').help_text,
        widget=selectable.AutoComboboxSelectWidget,
    )

    contact = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Contact',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(submit_label='Add')

    class Meta:
        model = Sponsorship
        fields = '__all__'
        widgets = {'event': HiddenInput, }


class SWCEventRequestForm(PrivacyConsentMixin, forms.ModelForm):
    captcha = ReCaptchaField()
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
    language = selectable.AutoCompleteSelectField(
        lookup_class=lookups.LanguageLookup,
        label='Language',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(wider_labels=True)

    class Meta:
        model = EventRequest
        exclude = ('active', 'created_at', 'last_updated_at', 'assigned_to',
                   'data_types', 'data_types_other',
                   'attendee_data_analysis_level', 'fee_waiver_request')
        widgets = {
            'approx_attendees': forms.RadioSelect(),
            'attendee_domains': forms.CheckboxSelectMultiple(),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_computing_levels': forms.CheckboxSelectMultiple(),
            'travel_reimbursement': forms.RadioSelect(),
            'admin_fee_payment': forms.RadioSelect(),
        }


class DCEventRequestForm(SWCEventRequestForm):
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

    class Meta(SWCEventRequestForm.Meta):
        exclude = ('active', 'created_at', 'last_updated_at', 'assigned_to',
                   'admin_fee_payment', 'attendee_computing_levels')
        widgets = {
            'approx_attendees': forms.RadioSelect(),
            'attendee_domains': forms.CheckboxSelectMultiple(),
            'data_types': forms.RadioSelect(),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_data_analysis_level': forms.CheckboxSelectMultiple(),
            'travel_reimbursement': forms.RadioSelect(),
        }


class EventSubmitFormNoCaptcha(forms.ModelForm):
    class Meta:
        model = EventSubmission
        exclude = ('active', 'created_at', 'last_updated_at', 'assigned_to')


class EventSubmitForm(EventSubmitFormNoCaptcha, PrivacyConsentMixin):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)


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
            'instructor_status': forms.RadioSelect(),
            'is_partner': forms.RadioSelect(),
            'domains': forms.CheckboxSelectMultiple(),
            'topics': forms.CheckboxSelectMultiple(),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_data_analysis_level': forms.CheckboxSelectMultiple(),
            'payment': forms.RadioSelect(),
        }


class DCSelfOrganizedEventRequestForm(
        DCSelfOrganizedEventRequestFormNoCaptcha, PrivacyConsentMixin):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)

    class Meta(DCSelfOrganizedEventRequestFormNoCaptcha.Meta):
        exclude = ('active', 'created_at', 'last_updated_at', 'assigned_to')


class ProfileUpdateRequestFormNoCaptcha(forms.ModelForm):
    languages = selectable.AutoCompleteSelectMultipleField(
        lookup_class=lookups.LanguageLookup,
        label='Languages you can teach in',
        required=False,
        widget=selectable.AutoComboboxSelectMultipleWidget,
    )

    class Meta:
        model = ProfileUpdateRequest
        exclude = ('active', 'created_at', 'last_updated_at')
        widgets = {
            'domains': forms.CheckboxSelectMultiple(),
            'lessons': forms.CheckboxSelectMultiple(),
            'occupation': forms.RadioSelect(),
            'gender': forms.RadioSelect(),
        }

    def clean_twitter(self):
        """Remove '@'s from the beginning of the Twitter handle."""
        twitter_handle = self.cleaned_data['twitter']
        return re.sub('^@+', '', twitter_handle)


class ProfileUpdateRequestForm(ProfileUpdateRequestFormNoCaptcha,
                               PrivacyConsentMixin):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)


class EventLookupForm(forms.Form):
    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = bootstrap_helper


class PersonLookupForm(forms.Form):
    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(use_get_method=True)


class AdminLookupForm(forms.Form):
    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.AdminLookup,
        label='Administrator',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = bootstrap_helper


class SimpleTodoForm(forms.ModelForm):
    helper = bootstrap_helper

    class Meta:
        model = TodoItem
        fields = ('title', 'due', 'additional', 'completed', 'event')
        widgets = {'event': HiddenInput, }

# `extra`: number of forms populated via `initial` parameter; it's hardcoded in
# `views.todos_add`
TodoFormSet = modelformset_factory(TodoItem, form=SimpleTodoForm, extra=10)


class EventsSelectionForm(forms.Form):
    event_a = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event A',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    event_b = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event B',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(use_get_method=True)


class EventsMergeForm(forms.Form):
    TWO = (
        ('obj_a', 'Use A'),
        ('obj_b', 'Use B'),
    )
    THREE = TWO + (('combine', 'Combine'), )
    DEFAULT = 'obj_a'

    event_a = forms.ModelChoiceField(queryset=Event.objects.all(),
                                     widget=forms.HiddenInput)

    event_b = forms.ModelChoiceField(queryset=Event.objects.all(),
                                     widget=forms.HiddenInput)

    id = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    slug = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    completed = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    assigned_to = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    start = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    end = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    host = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    administrator = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    tags = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    url = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    language = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    reg_key = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    admin_fee = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    invoice_status = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    attendance = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    contact = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    country = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    venue = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    address = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    latitude = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    longitude = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    learners_pre = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    learners_post = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    instructors_pre = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    instructors_post = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    learners_longterm = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    notes = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    task_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    todoitem_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )


class InvoiceRequestForm(forms.ModelForm):
    helper = bootstrap_helper

    class Meta:
        model = InvoiceRequest
        fields = (
            'organization', 'reason', 'reason_other', 'date', 'event',
            'event_location', 'item_id', 'postal_number', 'contact_name',
            'contact_email', 'contact_phone', 'full_address', 'amount',
            'currency', 'currency_other', 'breakdown', 'vendor_form_required',
            'vendor_form_link', 'form_W9', 'receipts_sent',
            'shared_receipts_link', 'notes',
        )
        widgets = {
            'reason': RadioSelect,
            'currency': RadioSelect,
            'vendor_form_required': RadioSelect,
            'receipts_sent': RadioSelect,
        }


class InvoiceRequestUpdateForm(forms.ModelForm):
    class Meta:
        model = InvoiceRequest
        fields = (
            'status', 'sent_date', 'paid_date', 'notes'
        )


class TrainingRequestForm(PrivacyConsentMixin, forms.ModelForm):
    agreed_to_code_of_conduct = forms.BooleanField(
        required=True,
        initial=False,
        label='*I agree to abide by Software and Data Carpentry\'s Code of Conduct',
        help_text='The Code of Conduct can be found at '
                  '<a href="http://software-carpentry.org/conduct/" target="_blank">'
                  'http://software-carpentry.org/conduct/</a>'
                  'and <a href="http://datacarpentry.org/code-of-conduct/" target="_blank">'
                  'http://datacarpentry.org/code-of-conduct/</a>',
    )
    agreed_to_complete_training = forms.BooleanField(
        required=True,
        initial=False,
        label='*I agree to complete this training within three months of the Training Course',
        help_text='The completion steps are described at '
                  '<a href="http://swcarpentry.github.io/instructor-training/checkout/" target="_blank">'
                  'http://swcarpentry.github.io/instructor-training/checkout/</a> '
                  'and take a total of approximately 8-10 hours.',
    )
    agreed_to_teach_workshops = forms.BooleanField(
        required=True,
        initial=False,
        label='*I agree to teach a Software Carpentry or Data Carpentry '
              'workshop within 12 months of this Training Course',
    )
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)

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
            'domains',
            'domains_other',
            'gender',
            'gender_other',
            'previous_involvement',
            'previous_training',
            'previous_training_other',
            'previous_training_explanation',
            'previous_experience',
            'previous_experience_other',
            'previous_experience_explanation',
            'programming_language_usage_frequency',
            'reason',
            'teaching_frequency_expectation',
            'teaching_frequency_expectation_other',
            'max_travelling_frequency',
            'max_travelling_frequency_other',
            'additional_skills',
            'comment',
        )
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
        }


class TrainingRequestUpdateForm(forms.ModelForm):
    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Matched Trainee',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
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


class AutoUpdateProfileForm(PrivacyConsentMixin, forms.ModelForm):
    username = forms.CharField(disabled=True, required=False)
    github = forms.CharField(
        disabled=True, required=False,
        help_text='If you want to change your github username, please email '
                  'us at <a href="mailto:admin@software-carpentry.org">'
                  'admin@software-carpentry.org</a>.')

    languages = selectable.AutoCompleteSelectMultipleField(
        lookup_class=lookups.LanguageLookup,
        label='Languages',
        required=False,
        widget=selectable.AutoComboboxSelectMultipleWidget,
    )

    helper = bootstrap_helper

    class Meta:
        model = Person
        fields = [
            'personal',
            'middle',
            'family',
            'email',
            'gender',
            'may_contact',
            'airport',
            'github',
            'twitter',
            'url',
            'username',
            'affiliation',
            'domains',
            'lessons',
            'languages',
        ]
        readonly_fields = (
            'username',
            'github',
        )
        widgets = {
            'occupation': forms.RadioSelect(),
            'gender': forms.RadioSelect(),
            'domains': forms.CheckboxSelectMultiple(),
            'lessons': forms.CheckboxSelectMultiple(),
        }


class TrainingProgressForm(forms.ModelForm):
    trainee = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Trainee',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )
    evaluated_by = selectable.AutoCompleteSelectField(
        lookup_class=lookups.AdminLookup,
        label='Evaluated by',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )
    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.TTTEventLookup,
        label='Event',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    # helper used in edit view
    helper = BootstrapHelper(duplicate_buttons_on_top=True,
                             submit_label='Update',
                             add_delete_button=True,
                             additional_form_class='training-progress')

    # helper used in create view
    create_helper = BootstrapHelper(duplicate_buttons_on_top=True,
                                    submit_label='Add',
                                    additional_form_class='training-progress')

    class Meta:
        model = TrainingProgress
        fields = [
            'trainee',
            'evaluated_by',
            'requirement',
            'state',
            'discarded',
            'event',
            'url',
            'notes',
        ]
        widgets = {
            'state': RadioSelect,
        }


class BulkAddTrainingProgressForm(forms.ModelForm):
    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.TTTEventLookup,
        label='Training',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
    )

    trainees = forms.ModelMultipleChoiceField(queryset=Person.objects.all())

    helper = BootstrapHelper(additional_form_class='training-progress',
                             submit_label='Add',
                             form_tag=False)
    helper.layout = Layout(
        # no 'trainees' -- you should take care of generating it manually in
        # the template where this form is used

        'requirement',
        'state',
        'event',
        'url',
        'notes',
    )

    class Meta:
        model = TrainingProgress
        fields = [
            # no 'trainees'
            'requirement',
            'state',
            'event',
            'url',
            'notes',
        ]
        widgets = {
            'state': RadioSelect,
            'notes': TextInput,
        }


class BulkDiscardProgressesForm(forms.Form):
    """Form used to bulk discard all TrainingProgresses associated with
    selected trainees."""

    trainees = forms.ModelMultipleChoiceField(queryset=Person.objects.all())

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False,
                             display_labels=False)

    SUBMIT_POPOVER = '''<p>Discarded progress will be displayed in the following
    way: <span class='label label-default'><strike> Discarded
    </strike></span>.</p>

    <p>If you want to permanently remove records from system,
    click one of the progress labels and, then, click "delete" button.</p>'''

    helper.layout = Layout(
        # no 'trainees' -- you should take care of generating it manually in
        # the template where this form is used

        # We use formnovalidate on submit button to disable browser
        # validation. This is necessary because this form is used along with
        # BulkAddTrainingProgressForm, which have required fields. Both forms
        # live inside the same <form> tag. Without this attribute, when you
        # click the following submit button, the browser reports missing
        # values in required fields in BulkAddTrainingProgressForm.
        Submit('discard',
               'Discard all progress of selected trainees',
               formnovalidate='formnovalidate',
               **{
                   'data-toggle': 'popover',
                   'data-html': 'true',
                   'data-content': SUBMIT_POPOVER,
               }),
        HTML('&nbsp;<a bulk-email-on-click class="btn btn-primary">'
             'Mail selected trainees</a>'),
    )


class BulkChangeTrainingRequestForm(forms.Form):
    """Form used to bulk discard training requests or bulk unmatch trainees
    from trainings."""

    requests = forms.ModelMultipleChoiceField(
        queryset=TrainingRequest.objects.all())

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False,
                             display_labels=False)
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
            Submit('discard', 'Discard selected requests',
                   formnovalidate='formnovalidate'),
            Submit('unmatch', 'Unmatch selected trainees from training',
                   formnovalidate='formnovalidate'),
            HTML('<a bulk-email-on-click class="btn btn-primary">'
                 'Mail selected trainees</a>&nbsp;'),
            HTML('<a class="btn btn-primary" href="{% url \'download_trainingrequests\' %}">'
                 'Download all requests as CSV</a>&nbsp;'),
            HTML('<a href="{% url \'training_request\' %}" class="btn btn-success">'
                 'Create new request</a>'),
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

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.TTTEventLookup,
        label='Training',
        required=True,
        widget=selectable.AutoComboboxSelectWidget,
    )

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False)
    helper.layout = Layout(
        'event',
    )
    helper.add_input(
        Submit(
           'match',
            'Match selected trainees to chosen training',
            **{
                'data-toggle': 'popover',
                'data-html': 'true',
                'data-content': 'If you want to <strong>re</strong>match '
                                'trainees to other training, first '
                                '<strong>unmatch</strong> them!',
            }
        )
    )

    def clean(self):
        super().clean()

        if any(r.person is None for r in self.cleaned_data.get('requests', [])):
            raise ValidationError('Some of the requests are not matched '
                                  'to a trainee yet. Before matching them to '
                                  'a training, you need to accept them '
                                  'and match with a trainee.')


class MatchTrainingRequestForm(forms.Form):
    """Form used to match a training request to a Person."""
    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Trainee Account',
        required=False,
        widget=selectable.AutoComboboxSelectWidget,
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


class SendHomeworkForm(forms.ModelForm):
    url = URLField(label='URL')

    def __init__(self, submit_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = BootstrapHelper(submit_name=submit_name)

    class Meta:
        model = TrainingProgress
        fields = [
            'url',
        ]
