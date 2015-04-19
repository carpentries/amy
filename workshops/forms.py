from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from selectable import forms as selectable

from workshops.models import Skill, Airport, Event, Task
from . import lookups


INSTRUCTOR_SEARCH_LEN = 10   # how many instrutors to return from a search by default


class BootstrapHelper(FormHelper):
    form_class = 'form-horizontal'
    label_class = 'col-lg-2'
    field_class = 'col-lg-8'

    def __init__(self, form=None):
        super().__init__(form)

        self.attrs['role'] = 'form'
        self.inputs.append(Submit('submit', 'Submit'))


class BootstrapHelperWithoutForm(BootstrapHelper):
    form_tag = False

bootstrap_helper = BootstrapHelper()
bootstrap_helper_without_form = BootstrapHelperWithoutForm()


class InstructorsForm(forms.Form):
    '''Represent instructor matching form.'''

    wanted = forms.IntegerField(label='Number Wanted',
                                initial=INSTRUCTOR_SEARCH_LEN,
                                min_value=1)
    latitude = forms.FloatField(label='Latitude',
                                min_value=-90.0,
                                max_value=90.0,
                                required=False)
    longitude = forms.FloatField(label='Longitude',
                                 min_value=-180.0,
                                 max_value=180.0,
                                 required=False)
    airport = forms.ModelChoiceField(label='airport',
                                     queryset=Airport.objects.all(),
                                     to_field_name='iata',
                                     required=False)

    def __init__(self, *args, **kwargs):
        '''Build checkboxes for skills dynamically.'''
        super(InstructorsForm, self).__init__(*args, **kwargs)
        skills = Skill.objects.all()
        for s in skills:
            self.fields[s.name] = forms.BooleanField(label=s.name, required=False)

    def clean(self):
        cleaned_data = super(InstructorsForm, self).clean()
        airport = cleaned_data.get('airport')
        lat = cleaned_data.get('latitude')
        long = cleaned_data.get('longitude')

        if airport is None:
            if lat is None or long is None:
                raise forms.ValidationError(
                    'Must specify either an airport code or latitude/longitude')
        else:
            if lat is not None or long is not None:
                raise forms.ValidationError(
                    'Cannot specify both an airport code and a '
                    'latitude/longitude. Pick one or the other')
            cleaned_data['latitude'] = airport.latitude
            cleaned_data['longitude'] = airport.longitude
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
    )

    organizer = selectable.AutoCompleteSelectField(
        lookup_class=lookups.SiteLookup,
        label='Organizer',
        required=True,
    )

    def clean_slug(self):
        # required for Event.get_by_ident
        data = self.cleaned_data['slug']
        if data and not re.match(r'^\d{4}-\d{2}-.+$', data):
            raise forms.ValidationError("Slug must begin with YYYY-MM- syntax")
        return data

    class Meta:
        model = Event
        exclude = tuple()


class TaskForm(forms.ModelForm):

    class Meta:
        model = Task
        exclude = ('event', )
