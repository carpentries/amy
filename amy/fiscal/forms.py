from crispy_forms.layout import Div, HTML, Field
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.dispatch import receiver
from markdownx.fields import MarkdownxFormField

from fiscal.models import MembershipTask
from workshops.forms import (
    BootstrapHelper,
    WidgetOverrideMixin,
    form_saved_add_comment,
    SELECT2_SIDEBAR,
)
from workshops.models import (
    Organization,
    Member,
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
    "data-width": "100%",
    "width": "style",
}


class OrganizationForm(forms.ModelForm):
    domain = forms.CharField(
        max_length=Organization._meta.get_field("domain").max_length,
        validators=[
            RegexValidator(
                r"[^\w\.-]+",
                inverse_match=True,
                message='Please enter only the domain (such as "math.esu.edu")'
                ' without a leading "http://" or a trailing "/".',
            )
        ],
    )

    helper = BootstrapHelper(add_cancel_button=False, duplicate_buttons_on_top=True)

    class Meta:
        model = Organization
        fields = ["domain", "fullname", "country"]


class OrganizationCreateForm(OrganizationForm):
    comment = MarkdownxFormField(
        label="Comment",
        help_text="This will be added to comments after the organization "
        "is created.",
        widget=forms.Textarea,
        required=False,
    )

    class Meta(OrganizationForm.Meta):
        fields = OrganizationForm.Meta.fields.copy()
        fields.append("comment")

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        create_comment_signal.send(
            sender=self.__class__,
            content_object=res,
            comment=self.cleaned_data["comment"],
            timestamp=None,
        )

        return res


class MembershipForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = Membership
        fields = [
            "name",
            "consortium",
            "public_status",
            "variant",
            "agreement_start",
            "agreement_end",
            "contribution_type",
            "registration_code",
            "agreement_link",
            "workshops_without_admin_fee_per_agreement",
            "self_organized_workshops_per_agreement",
            "seats_instructor_training",
            "additional_instructor_training_seats",
            "emergency_contact",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # add warning alert for dates falling within next 2-3 months
        INVALID_AGREEMENT_DURATION_WARNING = (
            "The selected agreement dates fall out of the typical 1-year long duration."
        )
        pos_index = self.helper.layout.fields.index("agreement_end")
        self.helper.layout.insert(
            pos_index + 1,
            Div(
                Div(
                    HTML(INVALID_AGREEMENT_DURATION_WARNING),
                    css_class="alert alert-warning offset-lg-2 col-lg-8 col-12",
                ),
                id="agreement_duration_warning",
                css_class="form-group row d-none",
            ),
        )

    def clean(self):
        super().clean()
        errors = dict()

        # validate agreement end date is no sooner than start date
        agreement_start = self.cleaned_data.get("agreement_start")
        agreement_end = self.cleaned_data.get("agreement_end")
        try:
            if agreement_end < agreement_start:
                errors["agreement_end"] = ValidationError(
                    "Agreement end date can't be sooner than the start date."
                )
        except TypeError:
            pass

        if errors:
            raise ValidationError(errors)


class MembershipCreateForm(MembershipForm):
    comment = MarkdownxFormField(
        label="Comment",
        help_text="This will be added to comments after the membership is created.",
        widget=forms.Textarea,
        required=False,
    )

    helper = BootstrapHelper(add_cancel_button=True)

    main_organization = forms.ModelChoiceField(
        Organization.objects.all(),
        label="Main organisation",
        required=True,
        widget=ModelSelect2Widget(data_view="organization-lookup"),
        help_text="Select main organisation (e.g. Signatory in case of consortium).",
    )

    class Meta(MembershipForm.Meta):
        fields = MembershipForm.Meta.fields.copy()
        fields.insert(0, "main_organization")
        fields.append("comment")

    class Media:
        js = ("membership_create.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["consortium"].help_text += (
            "<br>If you select this option, you'll be taken to the next screen to "
            "select organisations engaged in consortium."
        )

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        create_comment_signal.send(
            sender=self.__class__,
            content_object=res,
            comment=self.cleaned_data["comment"],
            timestamp=None,
        )

        return res


class MemberForm(forms.ModelForm):
    """Form intended to use in formset for creating multiple membership members."""

    helper = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )
    helper_empty_form = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )

    class Meta:
        model = Member
        fields = [
            "organization",
            "role",
        ]
        widgets = {
            "organization": ModelSelect2Widget(data_view="organization-lookup"),
            "role": ModelSelect2Widget(data_view="memberrole-lookup"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up layout objects for the helpers - they're identical except for
        # visibility of the delete checkbox
        self.helper.layout = self.helper.build_default_layout(self)
        self.helper_empty_form.layout = self.helper.build_default_layout(self)
        self.helper.layout.append(Field("id"))
        self.helper.layout.append(Field("DELETE"))  # visible; formset adds it
        self.helper_empty_form.layout.append(Field("id"))
        self.helper_empty_form.layout.append(
            Div(Field("DELETE"), css_class="d-none")  # hidden
        )


class MembershipTaskForm(forms.ModelForm):
    """Form intended to use in formset for creating multiple membership members."""

    helper = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )
    helper_empty_form = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )

    class Meta:
        model = MembershipTask
        fields = [
            "person",
            "role",
        ]
        widgets = {
            "person": ModelSelect2Widget(data_view="person-lookup"),
            "role": ModelSelect2Widget(data_view="membershippersonrole-lookup"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up layout objects for the helpers - they're identical except for
        # visibility of the delete checkbox
        self.helper.layout = self.helper.build_default_layout(self)
        self.helper_empty_form.layout = self.helper.build_default_layout(self)
        self.helper.layout.append(Field("id"))
        self.helper.layout.append(Field("DELETE"))  # visible; formset adds it
        self.helper_empty_form.layout.append(Field("id"))
        self.helper_empty_form.layout.append(
            Div(Field("DELETE"), css_class="d-none")  # hidden
        )


class SponsorshipForm(WidgetOverrideMixin, forms.ModelForm):

    helper = BootstrapHelper(submit_label="Add")

    class Meta:
        model = Sponsorship
        fields = "__all__"
        widgets = {
            "organization": ModelSelect2Widget(
                data_view="organization-lookup", attrs=SELECT2_SIDEBAR
            ),
            "event": ModelSelect2Widget(
                data_view="event-lookup", attrs=SELECT2_SIDEBAR
            ),
            "contact": ModelSelect2Widget(
                data_view="person-lookup", attrs=SELECT2_SIDEBAR
            ),
        }

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
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
