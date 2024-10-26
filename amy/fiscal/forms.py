from urllib.parse import urlparse, urlunparse

from crispy_forms.layout import HTML, Div
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.dispatch import receiver
from django.urls import reverse
from markdownx.fields import MarkdownxFormField

from fiscal.fields import FlexibleSplitArrayField
from fiscal.models import MembershipTask

# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import ModelSelect2MultipleWidget, ModelSelect2Widget
from workshops.forms import BootstrapHelper, form_saved_add_comment
from workshops.models import Member, Membership, Organization
from workshops.signals import create_comment_signal

# settings for Select2
# this makes it possible for autocomplete widget to fit in low-width sidebar
SIDEBAR_DAL_WIDTH = {
    "data-width": "100%",
    "width": "style",
}


class OrganizationForm(forms.ModelForm):
    domain = forms.URLField(widget=forms.TextInput)
    helper = BootstrapHelper(add_cancel_button=False, duplicate_buttons_on_top=True)

    class Meta:
        model = Organization
        fields = [
            "domain",
            "fullname",
            "country",
            "latitude",
            "longitude",
            "affiliated_organizations",
        ]
        widgets = {
            "affiliated_organizations": ModelSelect2MultipleWidget(
                data_view="organization-lookup"
            ),
        }

    def clean_domain(self):
        """Convert text into URL without scheme (http/https/etc)."""
        cleaned = self.cleaned_data["domain"]

        parsed_url = urlparse(cleaned)
        unparsed_url = urlunparse(
            parsed_url._replace(scheme="", params="", fragment="")
        )

        # after parsing-unparsing we may be left with scheme-less text
        # e.g. "//carpentries.org/lessons"; we obviously want to remove the slashes
        if unparsed_url.startswith("//"):
            domain = unparsed_url[2:]
        else:
            domain = unparsed_url

        return domain


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
    extensions = FlexibleSplitArrayField(
        forms.IntegerField(),
        size=0,
        help_text="Extensions are available for edit only if the membership has "
        "been extended.<br><b>Warning:</b> changing these will change the agreement "
        "end date.",
        required=False,
    )

    class Meta:
        model = Membership
        fields = [
            "name",
            "consortium",
            "public_status",
            "variant",
            "agreement_start",
            "agreement_end",
            "extensions",
            "contribution_type",
            "registration_code",
            "agreement_link",
            "workshops_without_admin_fee_per_agreement",
            "public_instructor_training_seats",
            "additional_public_instructor_training_seats",
            "inhouse_instructor_training_seats",
            "additional_inhouse_instructor_training_seats",
            "emergency_contact",
            "workshops_without_admin_fee_rolled_over",
            "workshops_without_admin_fee_rolled_from_previous",
            "public_instructor_training_seats_rolled_over",
            "public_instructor_training_seats_rolled_from_previous",
            "inhouse_instructor_training_seats_rolled_over",
            "inhouse_instructor_training_seats_rolled_from_previous",
        ]

    def __init__(
        self, *args, show_rolled_over=False, show_rolled_from_previous=False, **kwargs
    ):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")

        if instance and "extensions" in self.fields:
            # Recalculate number of subwidgets for each of the extensions.
            self.fields["extensions"].change_size(len(instance.extensions))

        # When editing membership, allow to edit rolled_over or rolled_from_previous
        # values when membership was rolled over or rolled from other membership.
        if not show_rolled_over:
            del self.fields["workshops_without_admin_fee_rolled_over"]
            del self.fields["public_instructor_training_seats_rolled_over"]
            del self.fields["inhouse_instructor_training_seats_rolled_over"]
        if not show_rolled_from_previous:
            del self.fields["workshops_without_admin_fee_rolled_from_previous"]
            del self.fields["public_instructor_training_seats_rolled_from_previous"]
            del self.fields["inhouse_instructor_training_seats_rolled_from_previous"]

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

        # check if multiple members are assigned - then disallow changing to
        # non-consortium
        new_consortium = self.cleaned_data.get("consortium")
        if not new_consortium and self.instance.pk:
            members_count = self.instance.member_set.count()
            if members_count > 1:
                errors["consortium"] = ValidationError(
                    "Cannot change to non-consortium when there are multiple members "
                    "assigned. Remove the members so that at most 1 is left."
                )

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
        fields.remove("extensions")
        fields.append("comment")

    class Media:
        js = ("membership_create.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["consortium"].help_text += (
            "<br>If you select this option, you'll be taken to the next screen to "
            "select organisations engaged in consortium. You must create the "
            "organisation (<a href='{}'>here</a>) before applying it to this "
            "membership."
        ).format(reverse("organization_add"))

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        create_comment_signal.send(
            sender=self.__class__,
            content_object=res,
            comment=self.cleaned_data["comment"],
            timestamp=None,
        )

        return res


class MembershipRollOverForm(MembershipCreateForm):
    main_organization = None  # remove the additional field

    copy_members = forms.BooleanField(
        label="Do you want to automatically copy member organisations from existing "
        "membership?",
        required=False,
        initial=True,
        help_text="If not consortium, the main organisation is always copied.",
    )
    copy_membership_tasks = forms.BooleanField(
        label="Do you want to automatically copy persons and their roles from existing "
        "membership?",
        required=False,
        initial=True,
    )

    class Meta(MembershipCreateForm.Meta):
        fields = [
            "name",
            "consortium",
            "copy_members",
            "copy_membership_tasks",
            "public_status",
            "variant",
            "agreement_start",
            "agreement_end",
            "contribution_type",
            "registration_code",
            "agreement_link",
            "workshops_without_admin_fee_per_agreement",
            "workshops_without_admin_fee_rolled_from_previous",
            "public_instructor_training_seats",
            "additional_public_instructor_training_seats",
            "public_instructor_training_seats_rolled_from_previous",
            "inhouse_instructor_training_seats",
            "additional_inhouse_instructor_training_seats",
            "inhouse_instructor_training_seats_rolled_from_previous",
            "emergency_contact",
            "comment",
        ]

    def __init__(self, *args, **kwargs):
        max_values = kwargs.pop("max_values", {})
        super().__init__(
            *args, show_rolled_over=True, show_rolled_from_previous=True, **kwargs
        )

        # don't allow values over the limit imposed by the view using this form
        fields = [
            "workshops_without_admin_fee_rolled_from_previous",
            "public_instructor_training_seats_rolled_from_previous",
            "inhouse_instructor_training_seats_rolled_from_previous",
        ]
        for field in fields:
            self[field].field.min_value = 0
            self[field].field.max_value = max_values.get(field, 0)
            # widget is already set up at this point, so alter it's attributes
            self[field].field.widget.attrs["max"] = self[field].field.max_value
            # overwrite any existing validators
            self[field].field.validators = [
                MinValueValidator(self[field].field.min_value),
                MaxValueValidator(self[field].field.max_value),
            ]

        # disable editing consortium
        self["consortium"].field.disabled = True

        # if not consortium, disable option to not copy members
        if self.initial.get("consortium", False) is False:
            self["copy_members"].field.disabled = True


class EditableFormsetFormMixin(forms.ModelForm):
    EDITABLE = forms.BooleanField(
        label="Change",
        required=False,
        widget=forms.CheckboxInput(attrs={"data-form-editable-check": ""}),
    )

    def clean(self):
        if self.has_changed() and not self.cleaned_data["EDITABLE"]:
            raise ValidationError("Form values weren't supposed to be changed.")
        return super().clean()


class MemberForm(EditableFormsetFormMixin, forms.ModelForm):
    """Form intended to use in formset for creating multiple membership members."""

    helper = BootstrapHelper(
        add_cancel_button=False,
        form_tag=False,
        add_submit_button=False,
        # formset gathers media, so there's no need to include them in every individual
        # form (plus this prevents an unnecessary bug when multiple handlers are
        # attached to the same element)
        include_media=False,
    )
    helper_deletable = BootstrapHelper(
        add_cancel_button=False,
        form_tag=False,
        add_submit_button=False,
        include_media=False,
    )
    helper_empty_form = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )
    helper_empty_form_deletable = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )

    class Media:
        js = ("member_form.js",)

    class Meta:
        model = Member
        fields = [
            # The membership field is required for uniqueness validation. We're making
            # it hidden from user to not confuse them, and to discourage from changing
            # field's value. The downside of this approach is that a) user can provide
            # different ID if they try hard enough, and b) tests get a little bit
            # harder as additional value has to be provided.
            "membership",
            "organization",
            "role",
        ]
        widgets = {
            "membership": forms.HiddenInput,
            "organization": ModelSelect2Widget(data_view="organization-lookup"),
            "role": ModelSelect2Widget(data_view="memberrole-lookup"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up layout objects for the helpers - they're identical except for
        # visibility of the delete checkbox
        self.helper.layout = self.helper.build_default_layout(self)
        self.helper.layout.append("id")

        self.helper_deletable.layout = self.helper.build_default_layout(self)
        self.helper_deletable.layout.append("id")
        self.helper_deletable.layout.append("DELETE")  # visible; formset adds it

        self.helper_empty_form.layout = self.helper.build_default_layout(self)
        self.helper_empty_form.layout.append("id")
        # remove EDITABLE checkbox from empty helper form
        pos_index = self.helper_empty_form.layout.fields.index("EDITABLE")
        self.helper_empty_form.layout.pop(pos_index)

        self.helper_empty_form_deletable.layout = self.helper.build_default_layout(self)
        self.helper_empty_form_deletable.layout.append("id")
        self.helper_empty_form_deletable.layout.append(
            Div("DELETE", css_class="d-none")  # hidden
        )
        # remove EDITABLE checkbox from empty helper deletable form
        pos_index = self.helper_empty_form_deletable.layout.fields.index("EDITABLE")
        self.helper_empty_form_deletable.layout.pop(pos_index)


class MembershipTaskForm(EditableFormsetFormMixin, forms.ModelForm):
    """Form intended to use in formset for creating multiple membership members."""

    helper = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )
    helper_deletable = BootstrapHelper(
        add_cancel_button=False,
        form_tag=False,
        add_submit_button=False,
        include_media=False,
    )
    helper_empty_form = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )
    helper_empty_form_deletable = BootstrapHelper(
        add_cancel_button=False, form_tag=False, add_submit_button=False
    )

    class Meta:
        model = MembershipTask
        fields = [
            # The membership field is required for uniqueness validation. We're making
            # it hidden from user to not confuse them, and to discourage from changing
            # field's value. The downside of this approach is that a) user can provide
            # different ID if they try hard enough, and b) tests get a little bit
            # harder as additional value has to be provided.
            "membership",
            "person",
            "role",
        ]
        widgets = {
            "membership": forms.HiddenInput,
            "person": ModelSelect2Widget(data_view="person-lookup"),
            "role": ModelSelect2Widget(data_view="membershippersonrole-lookup"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up layout objects for the helpers - they're identical except for
        # visibility of the delete checkbox
        self.helper.layout = self.helper.build_default_layout(self)
        self.helper.layout.append("id")
        self.helper.layout.append("DELETE")  # visible; formset adds it

        self.helper_deletable.layout = self.helper.build_default_layout(self)
        self.helper_deletable.layout.append("id")
        self.helper_deletable.layout.append("DELETE")  # visible; formset adds it

        self.helper_empty_form.layout = self.helper.build_default_layout(self)
        self.helper_empty_form.layout.append("id")
        self.helper_empty_form.layout.append(
            Div("DELETE", css_class="d-none")  # hidden
        )
        # remove EDITABLE checkbox from empty helper form
        pos_index = self.helper_empty_form.layout.fields.index("EDITABLE")
        self.helper_empty_form.layout.pop(pos_index)

        self.helper_empty_form_deletable.layout = self.helper.build_default_layout(self)
        self.helper_empty_form_deletable.layout.append("id")
        self.helper_empty_form_deletable.layout.append(
            Div("DELETE", css_class="d-none")  # hidden
        )


class MembershipExtensionForm(forms.Form):
    agreement_start = forms.DateField(disabled=True, required=False)
    agreement_end = forms.DateField(disabled=True, required=False)
    new_agreement_end = forms.DateField(required=True)
    extension = forms.IntegerField(
        disabled=True,
        required=False,
        help_text="Number of days the agreement will be extended.",
    )
    comment = MarkdownxFormField(
        label="Comment",
        help_text=(
            "This will be added to comments after the membership is extended. Beginning"
            " of the comment will be prefixed with information about length of the "
            "extension."
        ),
        widget=forms.Textarea,
        required=False,
    )

    helper = BootstrapHelper()

    class Media:
        js = ("membership_extend.js", "date_yyyymmdd.js")

    def clean(self):
        super().clean()
        errors = dict()

        # validate new agreement end date is later than original agreement end date
        agreement_end = self.cleaned_data.get("agreement_end")
        new_agreement_end = self.cleaned_data.get("new_agreement_end")
        try:
            if new_agreement_end <= agreement_end:
                errors["new_agreement_end"] = ValidationError(
                    "New agreement end date must be later than original agreement "
                    "end date."
                )
        except TypeError:
            pass

        if errors:
            raise ValidationError(errors)


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
