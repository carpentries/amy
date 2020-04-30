from django import forms
from django.core.validators import RegexValidator
from django.dispatch import receiver
from markdownx.fields import MarkdownxFormField

from workshops.forms import (
    BootstrapHelper,
    WidgetOverrideMixin,
    form_saved_add_comment,
    SELECT2_SIDEBAR,
)
from workshops.models import (
    Organization,
    Membership,
    Sponsorship,
)
# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import (
    ModelSelect2Widget,
)
from workshops.signals import create_comment_signal


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
        fields = ['domain', 'fullname', 'country']


class OrganizationCreateForm(OrganizationForm):
    comment = MarkdownxFormField(
        label='Comment',
        help_text='This will be added to comments after the organization '
                  'is created.',
        widget=forms.Textarea,
        required=False,
    )

    class Meta(OrganizationForm.Meta):
        fields = OrganizationForm.Meta.fields.copy()
        fields.append('comment')

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        create_comment_signal.send(sender=self.__class__,
                                   content_object=res,
                                   comment=self.cleaned_data['comment'],
                                   timestamp=None)

        return res


class MembershipForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    organization = forms.ModelChoiceField(
        label='Organization',
        required=True,
        queryset=Organization.objects.all(),
        widget=ModelSelect2Widget(data_view='organization-lookup')
    )

    class Meta:
        model = Membership
        fields = [
            'organization', 'variant', 'agreement_start', 'agreement_end',
            'contribution_type', 'workshops_without_admin_fee_per_agreement',
            'self_organized_workshops_per_agreement',
            'seats_instructor_training',
            'additional_instructor_training_seats',
        ]


class MembershipCreateForm(MembershipForm):
    comment = MarkdownxFormField(
        label='Comment',
        help_text='This will be added to comments after the membership is '
                  'created.',
        widget=forms.Textarea,
        required=False,
    )

    class Meta(MembershipForm.Meta):
        fields = MembershipForm.Meta.fields.copy()
        fields.append('comment')

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        create_comment_signal.send(sender=self.__class__,
                                   content_object=res,
                                   comment=self.cleaned_data['comment'],
                                   timestamp=None)

        return res


class SponsorshipForm(WidgetOverrideMixin, forms.ModelForm):

    helper = BootstrapHelper(submit_label='Add')

    class Meta:
        model = Sponsorship
        fields = '__all__'
        widgets = {
            'organization': ModelSelect2Widget(data_view='organization-lookup',
                                               attrs=SELECT2_SIDEBAR),
            'event': ModelSelect2Widget(data_view='event-lookup',
                                        attrs=SELECT2_SIDEBAR),
            'contact': ModelSelect2Widget(data_view='person-lookup',
                                          attrs=SELECT2_SIDEBAR),
        }

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop('form_tag', True)
        super().__init__(*args, **kwargs)
        self.helper = BootstrapHelper(add_cancel_button=False, form_tag=form_tag)


# ----------------------------------------------------------
# Signals

# adding @receiver decorator to the function defined in `workshops.forms`
form_saved_add_comment = receiver(
    create_comment_signal,
    sender=OrganizationCreateForm,
)(form_saved_add_comment)

# adding @receiver decorator to the function defined in `workshops.forms`
form_saved_add_comment = receiver(
    create_comment_signal,
    sender=MembershipCreateForm,
)(form_saved_add_comment)
