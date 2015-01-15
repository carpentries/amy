from django import forms

from workshops.models import Skill, Airport

INSTRUCTOR_SEARCH_LEN = 10   # how many instrutors to return from a search by default


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
