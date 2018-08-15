import re

from captcha.fields import ReCaptchaField
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Submit, Button, Field
from crispy_forms.bootstrap import AccordionGroup, Accordion
from dal import autocomplete
from dal_select2.widgets import Select2Multiple
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import (
    HiddenInput,
    SelectMultiple,
    CheckboxSelectMultiple,
    TextInput,
    modelformset_factory,
    RadioSelect,
    URLField,
)
from django_countries import Countries
from django_countries.fields import CountryField

from workshops import lookups
from workshops.models import (
    Award,
    Event,
    Lesson,
    Person,
    Task,
    Airport,
    Organization,
    EventRequest,
    ProfileUpdateRequest,
    TodoItem,
    Membership,
    Sponsorship,
    InvoiceRequest,
    EventSubmission,
    TrainingRequest,
    DCSelfOrganizedEventRequest,
    TrainingProgress,
    Tag,
    Language,
)


# settings for Select2
# this makes it possible for autocomplete widget to fit in low-width sidebar
SIDEBAR_DAL_WIDTH = {
    'data-width': '100%',
    'width': 'style',
}


class BootstrapHelper(FormHelper):
    """Layout and behavior for crispy-displayed forms."""
    html5_required = True
    form_id = 'main-form'

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
            self.label_class = 'col-12 col-lg-3'
            self.field_class = 'col-12 col-lg-7'
        elif display_labels:
            self.label_class = 'col-12 col-lg-2'
            self.field_class = 'col-12 col-lg-8'
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
                css_class='btn-danger float-right'))

        if add_cancel_button:
            self.add_input(Button(
                'cancel', 'Cancel',
                css_class='btn-secondary float-right',
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
              '"https://docs.carpentries.org/topic_folders/policies/privacy.html" target="_blank">'
              'the data privacy policy of The Carpentries</a>.',
        required=True)


class WidgetOverrideMixin:

    def __init__(self, *args, **kwargs):
        widgets = kwargs.pop('widgets', {})
        super().__init__(*args, **kwargs)
        for field, widget in widgets.items():
            self.fields[field].widget = widget


class RadioSelectWithOther(forms.RadioSelect):
    """A RadioSelect widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


class CheckboxSelectMultipleWithOthers(forms.CheckboxSelectMultiple):
    """A multiple choice widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


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
    airport = forms.ModelChoiceField(
        label='Airport',
        required=False,
        queryset=Airport.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='airport-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        )
    )
    languages = forms.ModelMultipleChoiceField(
        label='Languages',
        required=False,
        queryset=Language.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='language-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        )
    )

    country = forms.MultipleChoiceField(choices=[])

    lessons = forms.ModelMultipleChoiceField(
        queryset=Lesson.objects.all(),
        widget=SelectMultiple(),
        required=False,
    )

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
        self.fields['country'] = forms.MultipleChoiceField(
            choices=choices, required=False, widget=Select2Multiple,
        )

        self.helper = FormHelper(self)
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML('<h5 class="card-title">Location close to</h5>'),
                    'airport',
                    HTML('<hr>'),
                    'country',
                    HTML('<hr>'),
                    'latitude',
                    'longitude',
                    css_class='card-body'
                ),
                css_class='card',
            ),
            'instructor_badges',
            HTML('<hr>'),
            'was_helper',
            'was_organizer',
            'is_in_progress_trainee',
            'languages',
            'gender',
            'lessons',
            Submit('submit', 'Submit'),
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

    term = forms.CharField(label='Term',
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

    helper = BootstrapHelper(
        add_cancel_button=False,
        use_get_method=True,
    )


class DebriefForm(forms.Form):
    '''Represent general debrief form.'''
    begin_date = forms.DateField(
        label='Begin date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ]
    )
    end_date = forms.DateField(
        label='End date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ]
    )

    helper = BootstrapHelper(use_get_method=True)


class EventForm(forms.ModelForm):
    host = forms.ModelChoiceField(
        label='Host',
        required=True,
        help_text=Event._meta.get_field('host').help_text,
        queryset=Organization.objects.all(),
        widget=autocomplete.ModelSelect2(url='organization-lookup')
    )

    administrator = forms.ModelChoiceField(
        label='Administrator',
        required=False,
        help_text=Event._meta.get_field('administrator').help_text,
        queryset=Organization.objects.all(),
        widget=autocomplete.ModelSelect2(url='organization-lookup')
    )

    assigned_to = forms.ModelChoiceField(
        label='Assigned to',
        required=False,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin-lookup')
    )

    language = forms.ModelChoiceField(
        label='Language',
        required=False,
        queryset=Language.objects.all(),
        widget=autocomplete.ModelSelect2(url='language-lookup')
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
        # TODO: probably in the next release of Django Crispy Forms (>1.7.2)
        #       there will be a solid support for Accordion and AccordionGroup,
        #       but for now we have to do it manually
        Div(
            Div(HTML('Location details'), css_class='card-header'),
            Div('country',
                'venue',
                'address',
                'latitude',
                'longitude',
                css_class='card-body'),
            css_class='card mb-2'
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
            'tags': SelectMultiple(attrs={
                'size': Tag.ITEMS_VISIBLE_IN_SELECT_WIDGET
            }),
        }

    class Media:
        # thanks to this, {{ form.media }} in the template will generate
        # a <link href=""> (for CSS files) or <script src=""> (for JS files)
        js = (
            'date_yyyymmdd.js',
            'edit_from_url.js',
            'online_country.js',
        )


class TaskForm(WidgetOverrideMixin, forms.ModelForm):

    helper = BootstrapHelper()

    class Meta:
        model = Task
        fields = '__all__'
        widgets = {
            'person': autocomplete.ModelSelect2(url='person-lookup'),
            'event': autocomplete.ModelSelect2(url='event-lookup'),
        }


class PersonForm(forms.ModelForm):
    airport = forms.ModelChoiceField(
        label='Airport',
        required=False,
        queryset=Airport.objects.all(),
        widget=autocomplete.ModelSelect2(url='airport-lookup')
    )
    languages = forms.ModelMultipleChoiceField(
        label='Languages',
        required=False,
        queryset=Language.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='language-lookup')
    )

    helper = bootstrap_helper

    class Meta:
        model = Person
        # don't display the 'password', 'user_permissions',
        # 'groups' or 'is_superuser' fields
        # + reorder fields
        fields = [
            'username',
            'personal',
            'middle',
            'family',
            'may_contact',
            'publish_profile',
            'data_privacy_agreement',
            'email',
            'gender',
            'country',
            'airport',
            'affiliation',
            'github',
            'twitter',
            'url',
            'occupation',
            'orcid',
            'user_notes',
            'notes',
            'lessons',
            'domains',
            'languages',
        ]


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
    person_a = forms.ModelChoiceField(
        label='Person From',
        required=True,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='person-lookup')
    )

    person_b = forms.ModelChoiceField(
        label='Person To',
        required=True,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='person-lookup')
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
    publish_profile = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    data_privacy_agreement = forms.ChoiceField(
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
    trainingprogress_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )


class AwardForm(WidgetOverrideMixin, forms.ModelForm):

    helper = bootstrap_helper

    class Meta:
        model = Award
        fields = '__all__'
        widgets = {
            'person': autocomplete.ModelSelect2(url='person-lookup'),
            'event': autocomplete.ModelSelect2(url='event-lookup'),
            'awarded_by': autocomplete.ModelSelect2(url='admin-lookup'),
        }


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
    helper = bootstrap_helper

    organization = forms.ModelChoiceField(
        label='Organization',
        required=True,
        queryset=Organization.objects.all(),
        widget=autocomplete.ModelSelect2(url='organization-lookup')
    )

    class Meta:
        model = Membership
        fields = [
            'organization', 'variant', 'agreement_start', 'agreement_end',
            'contribution_type', 'workshops_without_admin_fee_per_agreement',
            'self_organized_workshops_per_agreement', 'notes',
        ]


class SponsorshipForm(WidgetOverrideMixin, forms.ModelForm):

    helper = BootstrapHelper(submit_label='Add')

    class Meta:
        model = Sponsorship
        fields = '__all__'
        widgets = {
            'organization': autocomplete.ModelSelect2(url='organization-lookup'),
            'event': autocomplete.ModelSelect2(url='event-lookup'),
            'contact': autocomplete.ModelSelect2(url='person-lookup'),
        }


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
    language = forms.ModelChoiceField(
        label='Language',
        required=False,
        queryset=Language.objects.all(),
        widget=autocomplete.ModelSelect2(url='language-lookup')
    )

    helper = BootstrapHelper(wider_labels=True)

    class Meta:
        model = EventRequest
        exclude = ('active', 'created_at', 'last_updated_at', 'assigned_to',
                   'data_types', 'data_types_other',
                   'attendee_data_analysis_level', 'fee_waiver_request',
                   'event', )
        widgets = {
            'approx_attendees': forms.RadioSelect(),
            'attendee_domains': CheckboxSelectMultipleWithOthers('attendee_domains_other'),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_computing_levels': forms.CheckboxSelectMultiple(),
            'travel_reimbursement': RadioSelectWithOther('travel_reimbursement_other'),
            'admin_fee_payment': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up RadioSelectWithOther widget so that it can display additional
        # field inline
        self['attendee_domains'].field.widget.other_field = self['attendee_domains_other']
        self['travel_reimbursement'].field.widget.other_field = self['travel_reimbursement_other']

        # remove that additional field
        self.helper.layout.fields.remove('attendee_domains_other')
        self.helper.layout.fields.remove('travel_reimbursement_other')


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
                   'admin_fee_payment', 'attendee_computing_levels',
                   'event', )
        widgets = {
            'approx_attendees': forms.RadioSelect(),
            'attendee_domains': CheckboxSelectMultipleWithOthers('attendee_domains_other'),
            'data_types': RadioSelectWithOther('data_types_other'),
            'attendee_academic_levels': forms.CheckboxSelectMultiple(),
            'attendee_data_analysis_level': forms.CheckboxSelectMultiple(),
            'travel_reimbursement': RadioSelectWithOther('travel_reimbursement_other'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up RadioSelectWithOther widget so that it can display additional
        # field inline
        self['attendee_domains'].field.widget.other_field = self['attendee_domains_other']
        self['data_types'].field.widget.other_field = self['data_types_other']
        self['travel_reimbursement'].field.widget.other_field = self['travel_reimbursement_other']

        # remove that additional field
        self.helper.layout.fields.remove('attendee_domains_other')
        self.helper.layout.fields.remove('data_types_other')
        self.helper.layout.fields.remove('travel_reimbursement_other')


class EventSubmitFormNoCaptcha(forms.ModelForm):
    class Meta:
        model = EventSubmission
        exclude = ('created_at', 'last_updated_at', )


class EventSubmitForm(EventSubmitFormNoCaptcha, PrivacyConsentMixin):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)

    class Meta(EventSubmitFormNoCaptcha.Meta):
        exclude = ('active', 'created_at', 'last_updated_at', 'assigned_to',
                   'event')


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
        exclude = ('active', 'created_at', 'last_updated_at', 'assigned_to',
                   'event')


class ProfileUpdateRequestFormNoCaptcha(forms.ModelForm):
    languages = forms.ModelMultipleChoiceField(
        label='Languages you can teach in',
        required=False,
        queryset=Language.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='language-lookup')
    )

    helper = BootstrapHelper(wider_labels=True)

    class Meta:
        model = ProfileUpdateRequest
        exclude = ('active', 'created_at', 'last_updated_at')
        widgets = {
            'occupation': RadioSelectWithOther('occupation_other'),
            'gender': RadioSelectWithOther('gender_other'),
            'domains': CheckboxSelectMultipleWithOthers('domains_other'),
            'lessons': CheckboxSelectMultipleWithOthers('lessons_other'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up RadioSelectWithOther widget so that it can display additional
        # field inline
        self['occupation'].field.widget.other_field = self['occupation_other']
        self['gender'].field.widget.other_field = self['gender_other']
        self['domains'].field.widget.other_field = self['domains_other']
        self['lessons'].field.widget.other_field = self['lessons_other']

        # remove that additional field
        self.helper.layout.fields.remove('occupation_other')
        self.helper.layout.fields.remove('gender_other')
        self.helper.layout.fields.remove('domains_other')
        self.helper.layout.fields.remove('lessons_other')

    def clean_twitter(self):
        """Remove '@'s from the beginning of the Twitter handle."""
        twitter_handle = self.cleaned_data['twitter']
        return re.sub('^@+', '', twitter_handle)


class ProfileUpdateRequestForm(ProfileUpdateRequestFormNoCaptcha):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)


class EventLookupForm(forms.Form):
    event = forms.ModelChoiceField(
        label='Event',
        required=True,
        queryset=Event.objects.all(),
        widget=autocomplete.ModelSelect2(url='event-lookup')
    )

    helper = bootstrap_helper


class PersonLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label='Person',
        required=True,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='person-lookup')
    )

    helper = BootstrapHelper(use_get_method=True)


class AdminLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label='Administrator',
        required=True,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin-lookup')
    )

    helper = BootstrapHelper(add_cancel_button=False)


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
    event_a = forms.ModelChoiceField(
        label='Event A',
        required=True,
        queryset=Event.objects.all(),
        widget=autocomplete.ModelSelect2(url='event-lookup')
    )

    event_b = forms.ModelChoiceField(
        label='Event B',
        required=True,
        queryset=Event.objects.all(),
        widget=autocomplete.ModelSelect2(url='event-lookup')
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


class TrainingRequestForm(forms.ModelForm):
    # agreement fields are moved to the model

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
            'underresourced',
            'domains',
            'domains_other',
            # 'gender',
            # 'gender_other',
            'underrepresented',
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
            # 'additional_skills',
            'comment',
            'data_privacy_agreement',
            'code_of_conduct_agreement',
            'training_completion_agreement',
            'workshop_teaching_agreement',
        )
        widgets = {
            'occupation': RadioSelectWithOther('occupation_other'),
            'domains': CheckboxSelectMultipleWithOthers('domains_other'),
            'gender': forms.RadioSelect(),
            'previous_involvement': forms.CheckboxSelectMultiple(),
            'previous_training': RadioSelectWithOther('previous_training_other'),
            'previous_experience': RadioSelectWithOther('previous_experience_other'),
            'programming_language_usage_frequency': forms.RadioSelect(),
            'teaching_frequency_expectation': RadioSelectWithOther('teaching_frequency_expectation_other'),
            'max_travelling_frequency': RadioSelectWithOther('max_travelling_frequency_other'),
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
        self.helper.layout.fields.remove('teaching_frequency_expectation_other')
        self.helper.layout.fields.remove('max_travelling_frequency_other')


class TrainingRequestUpdateForm(forms.ModelForm):
    person = forms.ModelChoiceField(
        label='Matched Trainee',
        required=False,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='person-lookup')
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
        widget=autocomplete.ModelSelect2(url='trainingrequest-lookup')
    )

    trainingrequest_b = forms.ModelChoiceField(
        label='Training request B',
        required=True,
        queryset=TrainingRequest.objects.all(),
        widget=autocomplete.ModelSelect2(url='trainingrequest-lookup')
    )

    helper = BootstrapHelper(use_get_method=True)


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


class AutoUpdateProfileForm(forms.ModelForm):
    username = forms.CharField(disabled=True, required=False)
    github = forms.CharField(
        disabled=True, required=False,
        help_text='If you want to change your github username, please email '
                  'us at <a href="mailto:team@carpentries.org">'
                  'team@carpentries.org</a>.')

    country = CountryField().formfield(
        required=False,
        help_text='Your country of residence.',
    )

    languages = forms.ModelMultipleChoiceField(
        label='Languages',
        required=False,
        queryset=Language.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='language-lookup')
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
            'publish_profile',
            'country',
            'airport',
            'github',
            'twitter',
            'url',
            'username',
            'affiliation',
            'domains',
            'lessons',
            'languages',
            'occupation',
            'orcid',
        ]
        readonly_fields = (
            'username',
            'github',
        )
        widgets = {
            'gender': forms.RadioSelect(),
            'domains': forms.CheckboxSelectMultiple(),
            'lessons': forms.CheckboxSelectMultiple(),
        }


class TrainingProgressForm(forms.ModelForm):
    trainee = forms.ModelChoiceField(
        label='Trainee',
        required=True,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='person-lookup')
    )
    evaluated_by = forms.ModelChoiceField(
        label='Evaluated by',
        required=False,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin-lookup')
    )
    event = forms.ModelChoiceField(
        label='Event',
        required=False,
        queryset=Event.objects.all(),
        widget=autocomplete.ModelSelect2(url='event-lookup')
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

    def clean(self):
        cleaned_data = super().clean()

        trainee = cleaned_data.get('trainee')

        # check if trainee has at least one training task
        training_tasks = trainee.get_training_tasks()

        if not training_tasks:
            raise ValidationError("It's not possible to add training progress "
                                  "to a trainee without any training task.")


class BulkAddTrainingProgressForm(forms.ModelForm):
    event = forms.ModelChoiceField(
        label='Training',
        required=False,
        queryset=Event.objects.filter(tags__name='TTT'),
        widget=autocomplete.ModelSelect2(url='ttt-event-lookup')
    )

    trainees = forms.ModelMultipleChoiceField(queryset=Person.objects.all())
    # TODO: add trainees lookup?
    # trainees = forms.ModelMultipleChoiceField(
    #     label='Trainees',
    #     required=False,
    #     queryset=Person.objects.all(),
    #     widget=autocomplete.ModelSelect2(url='person-lookup'),
    # )

    helper = BootstrapHelper(additional_form_class='training-progress',
                             submit_label='Add',
                             form_tag=False,
                             add_cancel_button=False)
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

    def clean(self):
        cleaned_data = super().clean()

        trainees = cleaned_data.get('trainees')

        # check if all trainees have at least one training task
        for trainee in trainees:
            training_tasks = trainee.get_training_tasks()

            if not training_tasks:
                raise ValidationError("It's not possible to add training "
                                      "progress to a trainee without any "
                                      "training task.")


class BulkDiscardProgressesForm(forms.Form):
    """Form used to bulk discard all TrainingProgresses associated with
    selected trainees."""

    trainees = forms.ModelMultipleChoiceField(queryset=Person.objects.all())
    # TODO: add trainees lookup?
    # trainees = forms.ModelMultipleChoiceField(
    #     label='Trainees',
    #     required=False,
    #     queryset=Person.objects.all(),
    #     widget=autocomplete.ModelSelect2(url='person-lookup'),
    # )

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False,
                             display_labels=False,
                             add_cancel_button=False)

    SUBMIT_POPOVER = '''<p>Discarded progress will be displayed in the following
    way: <span class='badge badge-dark'><strike>Discarded</strike></span>.</p>

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
                   'css_class': 'btn btn-warning',
               }),
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
    #     widget=autocomplete.ModelSelect2(url='???-lookup'),
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
            Submit('discard', 'Discard selected requests',
                   formnovalidate='formnovalidate'),
            Submit('unmatch', 'Unmatch selected trainees from training',
                   formnovalidate='formnovalidate'),
            HTML('<a bulk-email-on-click class="btn btn-primary text-white">'
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
        widget=autocomplete.ModelSelect2(url='ttt-event-lookup')
    )

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False,
                             add_cancel_button=False)
    helper.layout = Layout(
        'event',
    )
    helper.add_input(
        Submit(
           'match',
            'Accept & match selected trainees to chosen training',
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
    person = forms.ModelChoiceField(
        label='Trainee Account',
        required=False,
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2(url='person-lookup'),
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


class AllActivityOverTimeForm(forms.Form):
    start = forms.DateField(
        label='Begin date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ],
    )
    end = forms.DateField(
        label='End date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ],
    )

    helper = BootstrapHelper(use_get_method=True)


#----------------------------------------------------------
# Action required forms

class ActionRequiredPrivacyForm(forms.ModelForm):
    data_privacy_agreement = forms.BooleanField(
        label='*I have read and agree to <a href='
              '"https://docs.carpentries.org/topic_folders/policies/privacy.html" target="_blank">'
              'the data privacy policy of The Carpentries</a>.',
        required=True)

    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = Person
        fields = [
            'data_privacy_agreement',
            'may_contact',
            'publish_profile',
        ]
