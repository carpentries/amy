from django import forms

from workshops.models import Skill

class InstructorMatchForm(forms.Form):
    '''Represent instructor matching form.'''

    latitude = forms.CharField(label='Latitude', max_length=8)
    longitude = forms.CharField(label='Longitude', max_length=8)

    def __init__(self, *args, **kwargs):
        '''Build checkboxes for skills dynamically.'''
        super(InstructorMatchForm, self).__init__(*args, **kwargs)
        skills = Skill.objects.all()
        for s in skills:
            self.fields[s.id] = forms.BooleanField(label=s.name, required=False)
