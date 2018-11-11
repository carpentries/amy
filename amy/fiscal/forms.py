from django import forms
from django.core.validators import RegexValidator

from workshops.forms import (
    BootstrapHelper,
    WidgetOverrideMixin,
)
from workshops.models import (
    Organization,
    Membership,
    Sponsorship,
)
# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import (
    ModelSelect2,
)


# settings for Select2
# this makes it possible for autocomplete widget to fit in low-width sidebar
SIDEBAR_DAL_WIDTH = {
    'data-width': '100%',
    'width': 'style',
}


class OrganizationForm(forms.ModelForm):
    domain = forms.CharField(
        max_length=Organization._meta.get_field('domain').max_length,
        validators=[
            RegexValidator(
                r'[^\w\.-]+', inverse_match=True,
                message='Please enter only the domain (such as "math.esu.edu")'
                        ' without a leading "http://" or a trailing "/".')
        ],
    )

    helper = BootstrapHelper(add_cancel_button=False,
                             duplicate_buttons_on_top=True)

    class Meta:
        model = Organization
        fields = ['domain', 'fullname', 'country', 'notes']


class MembershipForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    organization = forms.ModelChoiceField(
        label='Organization',
        required=True,
        queryset=Organization.objects.all(),
        widget=ModelSelect2(url='organization-lookup')
    )

    class Meta:
        model = Membership
        fields = [
            'organization', 'variant', 'agreement_start', 'agreement_end',
            'contribution_type', 'workshops_without_admin_fee_per_agreement',
            'self_organized_workshops_per_agreement',
            'seats_instructor_training',
            'additional_instructor_training_seats',
            'notes',
        ]


class SponsorshipForm(WidgetOverrideMixin, forms.ModelForm):

    helper = BootstrapHelper(submit_label='Add')

    class Meta:
        model = Sponsorship
        fields = '__all__'
        widgets = {
            'organization': ModelSelect2(url='organization-lookup'),
            'event': ModelSelect2(url='event-lookup'),
            'contact': ModelSelect2(url='person-lookup'),
        }
