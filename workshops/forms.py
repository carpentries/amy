from django import forms
from django.forms import HiddenInput, CheckboxSelectMultiple

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Submit, Field
from crispy_forms.bootstrap import FormActions
from django_countries.fields import CountryField
from selectable import forms as selectable

from workshops.models import (
    Award, Event, Lesson, Person, Task, KnowledgeDomain,
)
from workshops import lookups

INSTRUCTORS_NUM = 10  # how many instrutors to return from a search by default

AUTOCOMPLETE_HELP_TEXT = (
    "Autocomplete field; type characters to view available options, "
    "then select desired item from list."
)

DATE_HELP_TEXT = "Select date using widget, or enter in YYYY-MM-DD format."


class BootstrapHelper(FormHelper):
    form_class = 'form-horizontal'
    label_class = 'col-lg-2'
    field_class = 'col-lg-8'

    def __init__(self, form=None):
        super().__init__(form)

        self.attrs['role'] = 'form'
        self.inputs.append(Submit('submit', 'Submit'))


class BootstrapHelperWithAdd(BootstrapHelper):
    def __init__(self, form=None):
        super().__init__(form)

        self.inputs[-1] = Submit('submit', 'Add')


class BootstrapHelperFilter(FormHelper):
    form_method = 'get'

    def __init__(self, form=None):
        super().__init__(form)
        self.attrs['role'] = 'form'
        self.inputs.append(Submit('', 'Submit'))


bootstrap_helper = BootstrapHelper()
bootstrap_helper_with_add = BootstrapHelperWithAdd()
bootstrap_helper_filter = BootstrapHelperFilter()


class InstructorsForm(forms.Form):
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

    country = CountryField().formfield(required=False)

    lessons = forms.ModelMultipleChoiceField(queryset=Lesson.objects.all(),
                                             widget=CheckboxSelectMultiple(),
                                             required=False)

    def __init__(self, *args, **kwargs):
        '''Build checkboxes for qualifications dynamically.'''
        super(InstructorsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Div(
                Div(
                    'latitude',
                    'longitude',
                    css_class='panel-body'
                ),
                css_class='panel panel-default ',
            ),
            HTML('<p>OR</p>'),
            Div(
                Div(
                    'airport',
                    css_class='panel-body'
                ),
                css_class='panel panel-default ',
            ),
            HTML('<p>OR</p>'),
            Div(
                Div(
                    'country',
                    css_class='panel-body'
                ),
                css_class='panel panel-default ',
            ),
            'lessons',
            FormActions(
                Submit('submit', 'Submit'),
            ),
        )

    def clean(self):
        cleaned_data = super(InstructorsForm, self).clean()
        airport = cleaned_data.get('airport')
        lat = cleaned_data.get('latitude')
        long = cleaned_data.get('longitude')
        country = cleaned_data.get('country')

        sum = bool(airport) + bool(lat and long) + bool(country)
        # user can specify only one: either airport, or lat&long, or country
        if sum != 1:
            raise forms.ValidationError('Must specify an airport, or latitude'
                                        ' and longitude, or a country.')
        return cleaned_data


class PersonBulkAddForm(forms.Form):
    '''Represent CSV upload form for bulk adding people.'''

    file = forms.FileField()


class SearchForm(forms.Form):
    '''Represent general searching form.'''

    term = forms.CharField(label='term',
                           max_length=100)
    in_sites = forms.BooleanField(label='in sites',
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


class EventForm(forms.ModelForm):

    site = selectable.AutoCompleteSelectField(
        lookup_class=lookups.SiteLookup,
        label='Site',
        required=True,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    organizer = selectable.AutoCompleteSelectField(
        lookup_class=lookups.SiteLookup,
        label='Organizer',
        required=False,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start'].help_text = DATE_HELP_TEXT
        self.fields['end'].help_text = DATE_HELP_TEXT

    def clean_slug(self):
        # Ensure slug is not an integer value for Event.get_by_ident
        data = self.cleaned_data['slug']

        try:
            int(data)
        except ValueError:
            pass
        else:
            raise forms.ValidationError("Slug must not be an integer-value.")

        return data

    class Meta:
        model = Event
        # reorder fields, don't display 'deleted' field
        fields = ('slug', 'start', 'end', 'site', 'organizer',
                  'tags', 'url', 'reg_key', 'admin_fee', 'invoiced',
                  'attendance', 'notes')

    class Media:
        # thanks to this, {{ form.media }} in the template will generate
        # a <link href=""> (for CSS files) or <script src=""> (for JS files)
        js = ('calendar_popup.js', )


class TaskForm(forms.ModelForm):

    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person',
        required=True,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    class Meta:
        model = Task
        fields = '__all__'
        widgets = {'event': HiddenInput}


class TaskFullForm(TaskForm):

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=True,
        help_text=AUTOCOMPLETE_HELP_TEXT,
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
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    lessons = forms.ModelMultipleChoiceField(required=False,
                                             queryset=Lesson.objects.all())

    domains = forms.ModelMultipleChoiceField(
        required=False, queryset=KnowledgeDomain.objects.all()
    )

    class Meta:
        model = Person
        # don't display the 'password', 'user_permissions',
        # 'groups' or 'is_superuser' fields
        # + reorder fields
        fields = ['username', 'personal', 'middle', 'family', 'may_contact',
                  'email', 'gender', 'airport', 'affiliation', 'github',
                  'twitter', 'url', 'notes', 'lessons', 'domains']


class PersonPermissionsForm(forms.ModelForm):
    class Meta:
        model = Person
        # only display 'user_permissions', 'groups' and `is_superuser` fields
        fields = [
            'is_superuser',
            'user_permissions',
            'groups',
        ]


class PersonMergeForm(forms.Form):

    person_from = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person From',
        required=True,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    person_to = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person To',
        required=True,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )


class BadgeAwardForm(forms.ModelForm):

    person = selectable.AutoCompleteSelectField(
        lookup_class=lookups.PersonLookup,
        label='Person',
        required=True,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=False,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    class Meta:
        model = Award
        fields = '__all__'
        widgets = {'badge': HiddenInput}


class PersonAwardForm(forms.ModelForm):

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=False,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    class Meta:
        model = Award
        fields = '__all__'
        widgets = {'person': HiddenInput}


class PersonTaskForm(forms.ModelForm):

    event = selectable.AutoCompleteSelectField(
        lookup_class=lookups.EventLookup,
        label='Event',
        required=True,
        help_text=AUTOCOMPLETE_HELP_TEXT,
        widget=selectable.AutoComboboxSelectWidget,
    )

    class Meta:
        model = Task
        fields = '__all__'
        widgets = {'person': HiddenInput}
