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

    def get_lat_long(self):
        '''Get validity, latitude, and longitude.'''

        iata = self.cleaned_data['airport']
        lat = self.cleaned_data['latitude']
        long = self.cleaned_data['longitude']

        # No airport, so must have latitude and longitude
        if iata is None:
            if (lat is None) or (long is None):
                return False, None, None
            return True, lat, long

        # Airport, so cannot have latitude or longitude
        else:
            if (lat is not None) or (long is not None):
                return False, None, None
            airport = Airport.objects.get(iata=iata)
            return True, airport.latitude, airport.longitude

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
