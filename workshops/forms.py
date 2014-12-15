from django import forms

class InstructorMatchForm(forms.Form):
    '''Represent instructor matching form.'''

    latitude = forms.CharField(label='Latitude', max_length=8)
    longitude = forms.CharField(label='Longitude', max_length=8)
