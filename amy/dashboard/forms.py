from django import forms
from django_countries.fields import CountryField

from workshops.models import (
    Language,
    Person,
    TrainingProgress,
)

from workshops.forms import BootstrapHelper
# this is used instead of Django Autocomplete Light widgets
# see issue #1330
from workshops.fields import (
    Select2,
    Select2Multiple,
    ListSelect2,
    ModelSelect2,
    ModelSelect2Multiple,
    TagSelect2,
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
        widget=ListSelect2(),
    )

    languages = forms.ModelMultipleChoiceField(
        label='Languages',
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2Multiple(url='language-lookup')
    )

    helper = BootstrapHelper(add_cancel_button=False)

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
            'airport': ListSelect2(),
        }


class SendHomeworkForm(forms.ModelForm):
    url = forms.URLField(label='URL')

    def __init__(self, submit_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = BootstrapHelper(submit_name=submit_name,
                                      add_cancel_button=False)

    class Meta:
        model = TrainingProgress
        fields = [
            'url',
        ]
