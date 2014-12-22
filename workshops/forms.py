from django import forms

from workshops.models import Skill

INSTRUCTOR_SEARCH_LEN = 10   # how many instrutors to return from a search by default


class InstructorMatchForm(forms.Form):
    '''Represent instructor matching form.'''

    wanted = forms.IntegerField(label='Number Wanted',
                                initial=INSTRUCTOR_SEARCH_LEN,
                                min_value=1)
    latitude = forms.FloatField(label='Latitude',
                                min_value=-90.0,
                                max_value=90.0)
    longitude = forms.FloatField(label='Longitude',
                                 min_value=-180.0,
                                 max_value=180.0)

    def __init__(self, *args, **kwargs):
        '''Build checkboxes for skills dynamically.'''
        super(InstructorMatchForm, self).__init__(*args, **kwargs)
        skills = Skill.objects.all()
        for s in skills:
            self.fields[s.name] = forms.BooleanField(label=s.name, required=False)

class PersonBulkAddForm(forms.Form):
    '''Represent CSV upload form for bulk adding people.'''

    file = forms.FileField()
    #CHOICES = (('true', 'Yes, the first row contains headers.',), ('false', 'No.',))
    #has_header = forms.ChoiceField(label="Does the .CSV file have a header?", required=False, choices=CHOICES)

class PersonBuildAddConfirmForm(forms.Form):

    load = forms.BooleanField(label="Load people?", required=True)