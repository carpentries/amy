from datetime import datetime, timezone
import re

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Div, Field, Layout, Submit
from django import forms
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.forms import CheckboxSelectMultiple, SelectMultiple, TextInput
from django_comments.models import Comment
from django_countries import Countries
from django_countries.fields import CountryField
from markdownx.fields import MarkdownxFormField

from dashboard.models import Continent

# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import (
    ModelSelect2MultipleWidget,
    ModelSelect2Widget,
    RadioSelectWithOther,
    Select2MultipleWidget,
    Select2TagWidget,
    Select2Widget,
)
from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    GenderMixin,
    KnowledgeDomain,
    Language,
    Lesson,
    Membership,
    Organization,
    Person,
    Tag,
    Task,
)
from workshops.signals import create_comment_signal

# this makes it possible for Select2 autocomplete widget to fit in low-width sidebar
SELECT2_SIDEBAR = {
    "data-width": "100%",
    "width": "style",
}


class BootstrapHelper(FormHelper):
    """Layout and behavior for crispy-displayed forms."""

    html5_required = True
    form_id = "main-form"

    def __init__(
        self,
        form=None,
        duplicate_buttons_on_top=False,
        submit_label="Submit",
        submit_name="submit",
        submit_onclick=None,
        use_get_method=False,
        wider_labels=False,
        add_submit_button=True,
        add_delete_button=False,
        add_cancel_button=True,
        additional_form_class="",
        form_tag=True,
        display_labels=True,
        form_action=None,
        form_id=None,
        include_media=True,
    ):
        """
        `duplicate_buttons_on_top` -- Whether submit buttons should be
        displayed on both top and bottom of the form.

        `use_get_method` -- Force form to use GET instead of default POST.

        `wider_labels` -- SWCEventRequestForm and DCEventRequestForm have
        long labels, so this flag (set to True) is used to address that issue.

        `add_delete_button` -- displays additional red "delete" button.
        If you want to use it, you need to include in your template the
        following code:

            <form action="delete?next={{ request.GET.next|urlencode }}" method="POST"
                  id="delete-form">
              {% csrf_token %}
            </form>

        This is necessary, because delete button must be reassigned from the
        form using this helper to "delete-form". This reassignment is done
        via HTML5 "form" attribute on the "delete" button.

        `display_labels` -- Set to False, when your form has only submit
        buttons and you want these buttons to be aligned to left.
        """

        super().__init__(form)

        self.attrs["role"] = "form"

        self.duplicate_buttons_on_top = duplicate_buttons_on_top

        self.submit_label = submit_label

        if use_get_method:
            self.form_method = "get"

        if wider_labels:
            assert display_labels
            self.label_class = "col-12 col-lg-3"
            self.field_class = "col-12 col-lg-9"
        elif display_labels:
            self.label_class = "col-12 col-lg-2"
            self.field_class = "col-12 col-lg-10"
        else:
            self.label_class = ""
            self.field_class = "col-lg-12"

        if add_submit_button:
            self.add_input(
                Submit(
                    submit_name,
                    submit_label,
                    onclick=submit_onclick,
                )
            )

        if add_delete_button:
            self.add_input(
                Submit(
                    "delete",
                    "Delete",
                    onclick="return " 'confirm("Are you sure you want to delete it?");',
                    form="delete-form",
                    css_class="btn-danger float-right",
                )
            )

        if add_cancel_button:
            self.add_input(
                Button(
                    "cancel",
                    "Cancel",
                    css_class="btn-secondary float-right",
                    onclick="window.history.back()",
                )
            )

        # offset here adds horizontal centering for all these forms
        self.form_class = "form-horizontal " + additional_form_class

        self.form_tag = form_tag

        if form_action is not None:
            self.form_action = form_action

        if form_id is not None:
            self.form_id = form_id

        # don't prevent from loading media by default
        self.include_media = include_media

    def hr(self):
        """Horizontal line as a separator in forms is used very often. But
        since from time to time the forms are changed (in terms of columns
        width), we should rather use one global <hr>..."""
        return '<hr class="col-12 mx-0 px-0">'


class BootstrapHelperFilter(FormHelper):
    """A differently shaped forms (more space-efficient) for use in sidebar as
    filter forms."""

    form_method = "get"
    form_id = "filter-form"

    def __init__(self, form=None):
        super().__init__(form)
        self.attrs["role"] = "form"
        self.inputs.append(Submit("", "Submit"))


class BootstrapHelperFormsetInline(BootstrapHelper):
    """For use in inline formsets."""

    template = "bootstrap/table_inline_formset.html"


bootstrap_helper_filter = BootstrapHelperFilter()
bootstrap_helper_inline_formsets = BootstrapHelperFormsetInline()


# ----------------------------------------------------------
# MixIns


class PrivacyConsentMixin(forms.Form):
    privacy_consent = forms.BooleanField(
        label="*I have read and agree to <a href="
        '"https://docs.carpentries.org/topic_folders/policies/privacy.html"'
        ' target="_blank" rel="noreferrer">'
        "the data privacy policy of The Carpentries</a>.",
        required=True,
    )


class WidgetOverrideMixin:
    def __init__(self, *args, **kwargs):
        widgets = kwargs.pop("widgets", {})
        super().__init__(*args, **kwargs)
        for field, widget in widgets.items():
            self.fields[field].widget = widget


# ----------------------------------------------------------
# Forms


def continent_list():
    """This has to be as a callable, because otherwise Django evaluates this
    query and, if the database doesn't exist yet (e.g. during Travis-CI
    tests)."""
    return [("", "")] + list(Continent.objects.values_list("pk", "name"))


class WorkshopStaffForm(forms.Form):
    """Represent instructor matching form."""

    latitude = forms.FloatField(
        label="Latitude", min_value=-90.0, max_value=90.0, required=False
    )
    longitude = forms.FloatField(
        label="Longitude", min_value=-180.0, max_value=180.0, required=False
    )
    airport = forms.ModelChoiceField(
        label="Airport",
        required=False,
        queryset=Airport.objects.all(),
        widget=ModelSelect2Widget(data_view="airport-lookup", attrs=SELECT2_SIDEBAR),
    )
    languages = forms.ModelMultipleChoiceField(
        label="Languages",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2MultipleWidget(
            data_view="language-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )
    domains = forms.ModelMultipleChoiceField(
        label="Knowlege Domains",
        required=False,
        queryset=KnowledgeDomain.objects.all(),
        widget=ModelSelect2MultipleWidget(
            data_view="knowledge-domains-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )
    country = forms.MultipleChoiceField(
        choices=list(Countries()),
        required=False,
        widget=Select2MultipleWidget,
    )

    continent = forms.ChoiceField(
        choices=continent_list,
        required=False,
        widget=Select2Widget,
    )

    lessons = forms.ModelMultipleChoiceField(
        queryset=Lesson.objects.all(),
        widget=SelectMultiple(),
        required=False,
    )

    badges = forms.ModelMultipleChoiceField(
        queryset=Badge.objects.instructor_badges(),
        widget=CheckboxSelectMultiple(),
        required=False,
    )

    is_trainer = forms.BooleanField(required=False, label="Has Trainer badge")

    GENDER_CHOICES = ((None, "---------"),) + Person.GENDER_CHOICES
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)

    was_helper = forms.BooleanField(
        required=False, label="Was helper at least once before"
    )
    was_organizer = forms.BooleanField(
        required=False, label="Was organizer at least once before"
    )
    is_in_progress_trainee = forms.BooleanField(
        required=False, label="Is an in-progress instructor trainee"
    )

    def __init__(self, *args, **kwargs):
        """Build form layout dynamically."""
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_method = "get"
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML('<h5 class="card-title">Location</h5>'),
                    "airport",
                    HTML("<hr>"),
                    "country",
                    HTML("<hr>"),
                    "continent",
                    HTML("<hr>"),
                    "latitude",
                    "longitude",
                    css_class="card-body",
                ),
                css_class="card",
            ),
            "badges",
            "is_trainer",
            HTML("<hr>"),
            "was_helper",
            "was_organizer",
            "is_in_progress_trainee",
            "languages",
            "domains",
            "gender",
            "lessons",
            Submit("", "Submit"),
        )

    def clean(self):
        cleaned_data = super().clean()
        lat = bool(cleaned_data.get("latitude"))
        lng = bool(cleaned_data.get("longitude"))
        airport = bool(cleaned_data.get("airport"))
        country = bool(cleaned_data.get("country"))
        latlng = lat and lng

        # if searching by coordinates, then there must be both lat & lng
        # present
        if lat ^ lng:
            raise ValidationError(
                "Must specify both latitude and longitude if searching by "
                "coordinates"
            )

        # User must search by airport, or country, or coordinates, or none
        # of them. Sum of boolean elements must be equal 0 (if general search)
        # or 1 (if searching by airport OR country OR lat/lng).
        if sum([airport, country, latlng]) not in [0, 1]:
            raise ValidationError(
                "Must specify an airport OR a country, OR use coordinates, OR "
                "none of them."
            )
        return cleaned_data


class BulkUploadCSVForm(forms.Form):
    """This form allows to upload a single file; it's used by person bulk
    upload and training request manual score bulk upload."""

    file = forms.FileField()


class EventForm(forms.ModelForm):
    administrator = forms.ModelChoiceField(
        label="Administrator",
        required=True,
        help_text=Event._meta.get_field("administrator").help_text,
        queryset=Organization.objects.administrators(),
        widget=ModelSelect2Widget(data_view="administrator-org-lookup"),
    )

    assigned_to = forms.ModelChoiceField(
        label="Assigned to",
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="admin-lookup"),
    )

    language = forms.ModelChoiceField(
        label="Language",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2Widget(data_view="language-lookup"),
    )

    country = CountryField().formfield(
        required=False,
        help_text=Event._meta.get_field("country").help_text,
        widget=Select2Widget,
    )

    comment = MarkdownxFormField(
        label="Comment",
        help_text="Any content in here will be added to comments after this "
        "event is saved.",
        widget=forms.Textarea,
        required=False,
    )

    helper = BootstrapHelper(add_cancel_button=False, duplicate_buttons_on_top=True)

    class Meta:
        model = Event
        fields = [
            "slug",
            "completed",
            "start",
            "end",
            "host",
            "sponsor",
            "administrator",
            "assigned_to",
            "tags",
            "url",
            "language",
            "reg_key",
            "venue",
            "manual_attendance",
            "contact",
            "country",
            "address",
            "latitude",
            "longitude",
            "open_TTT_applications",
            "curricula",
            "lessons",
            "public_status",
            "instructors_pre",
            "instructors_post",
            "comment",
        ]
        widgets = {
            "host": ModelSelect2Widget(data_view="organization-lookup"),
            "sponsor": ModelSelect2Widget(data_view="organization-lookup"),
            "manual_attendance": TextInput,
            "latitude": TextInput,
            "longitude": TextInput,
            "tags": SelectMultiple(attrs={"size": Tag.ITEMS_VISIBLE_IN_SELECT_WIDGET}),
            "curricula": CheckboxSelectMultiple(),
            "lessons": CheckboxSelectMultiple(),
            "contact": Select2TagWidget,
        }

    class Media:
        js = (
            "date_yyyymmdd.js",
            "edit_from_url.js",
            "online_country.js",
        )

    def __init__(self, *args, **kwargs):
        show_lessons = kwargs.pop("show_lessons", False)
        add_comment = kwargs.pop("add_comment", True)
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            Field("slug", placeholder="YYYY-MM-DD-location"),
            "completed",
            Field("start", placeholder="YYYY-MM-DD"),
            Field("end", placeholder="YYYY-MM-DD"),
            "host",
            "sponsor",
            "administrator",
            "public_status",
            "assigned_to",
            "tags",
            "open_TTT_applications",
            "curricula",
            "url",
            "language",
            "reg_key",
            "manual_attendance",
            "contact",
            "instructors_pre",
            "instructors_post",
            Div(
                Div(HTML("Location details"), css_class="card-header"),
                Div(
                    "country",
                    "venue",
                    "address",
                    "latitude",
                    "longitude",
                    css_class="card-body",
                ),
                css_class="card mb-2",
            ),
        )

        # if we want to show lessons, we need to alter existing layout
        # otherwise we should remove the field so it doesn't break validation
        if show_lessons:
            self.helper.layout.insert(
                # insert AFTER the curricula
                self.helper.layout.fields.index("curricula") + 1,
                "lessons",
            )
        else:
            del self.fields["lessons"]

        if add_comment:
            self.helper.layout.append("comment")
        else:
            del self.fields["comment"]

    def clean_slug(self):
        # Ensure slug is in "YYYY-MM-DD-location" format
        data = self.cleaned_data["slug"]
        match = re.match(r"(\d{4}|x{4})-(\d{2}|x{2})-(\d{2}|x{2})-.+", data)
        if not match:
            raise ValidationError(
                'Slug must be in "YYYY-MM-DD-location"'
                ' format, where "YYYY", "MM", "DD" can'
                ' be unspecified (ie. "xx").'
            )
        return data

    def clean_end(self):
        """Ensure end >= start."""
        start = self.cleaned_data["start"]
        end = self.cleaned_data["end"]

        if start and end and end < start:
            raise ValidationError("Must not be earlier than start date.")
        return end

    def clean_open_TTT_applications(self):
        """Ensure there's a TTT tag applied to the event, if the
        `open_TTT_applications` is True."""
        open_TTT_applications = self.cleaned_data["open_TTT_applications"]
        tags = self.cleaned_data.get("tags", None)
        error_msg = "You cannot open applications on a non-TTT event."

        if open_TTT_applications and tags:
            # find TTT tag
            TTT_tag = False
            for tag in tags:
                if tag.name == "TTT":
                    TTT_tag = True
                    break

            if not TTT_tag:
                raise ValidationError(error_msg)

        elif open_TTT_applications:
            raise ValidationError(error_msg)

        return open_TTT_applications

    def clean_curricula(self):
        """Validate tags when some curricula are selected."""
        curricula = self.cleaned_data["curricula"]
        tags = self.cleaned_data["tags"]

        try:
            expected_tags = []
            for c in curricula:
                if c.active and c.carpentry:
                    expected_tags.append(c.carpentry)
                elif c.active and c.mix_match:
                    expected_tags.append("Circuits")
        except (ValueError, TypeError):
            expected_tags = []

        for tag in expected_tags:
            if not tags.filter(name=tag):
                raise forms.ValidationError(
                    "You must add tags corresponding to these curricula."
                )

        return curricula

    def clean_manual_attendance(self):
        """Regression: #1608 - fix 500 server error when field is cleared."""
        manual_attendance = self.cleaned_data["manual_attendance"] or 0
        return manual_attendance

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        comment = self.cleaned_data.get("comment")
        if comment:
            create_comment_signal.send(
                sender=self.__class__,
                content_object=res,
                comment=comment,
                timestamp=None,
            )

        return res


class EventCreateForm(EventForm):
    comment = MarkdownxFormField(
        label="Comment",
        help_text="This will be added to comments after the event is created.",
        widget=forms.Textarea,
        required=False,
    )


class TaskForm(WidgetOverrideMixin, forms.ModelForm):
    SEAT_MEMBERSHIP_HELP_TEXT = (
        "{}<br><b>Hint:</b> you can use input format YYYY-MM-DD to display "
        "memberships available on that date.".format(
            Task._meta.get_field("seat_membership").help_text
        )
    )
    seat_membership = forms.ModelChoiceField(
        label=Task._meta.get_field("seat_membership").verbose_name,
        help_text=SEAT_MEMBERSHIP_HELP_TEXT,
        required=False,
        queryset=Membership.objects.all(),
        widget=ModelSelect2Widget(
            data_view="membership-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )

    class Meta:
        model = Task
        fields = [
            "event",
            "person",
            "role",
            "title",
            "url",
            "seat_membership",
            "seat_public",
            "seat_open_training",
        ]
        widgets = {
            "person": ModelSelect2Widget(
                data_view="person-lookup", attrs=SELECT2_SIDEBAR
            ),
            "event": ModelSelect2Widget(
                data_view="event-lookup", attrs=SELECT2_SIDEBAR
            ),
            "seat_public": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        failed_trainings = kwargs.pop("failed_trainings", False)
        super().__init__(*args, **kwargs)
        bootstrap_kwargs = {
            "add_cancel_button": False,
            "form_tag": form_tag,
        }
        if failed_trainings:
            bootstrap_kwargs["submit_onclick"] = (
                'return confirm("Warning: Trainee failed previous training(s).'
                ' Are you sure you want to continue?");'
            )
        self.helper = BootstrapHelper(**bootstrap_kwargs)


class PersonForm(forms.ModelForm):
    airport = forms.ModelChoiceField(
        label="Airport",
        required=False,
        queryset=Airport.objects.all(),
        widget=ModelSelect2Widget(data_view="airport-lookup"),
    )
    languages = forms.ModelMultipleChoiceField(
        label="Languages",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2MultipleWidget(data_view="language-lookup"),
    )

    helper = BootstrapHelper(add_cancel_button=False, duplicate_buttons_on_top=True)

    class Meta:
        model = Person
        # don't display the 'password', 'user_permissions',
        # 'groups' or 'is_superuser' fields
        # + reorder fields
        fields = [
            "username",
            "personal",
            "middle",
            "family",
            "may_contact",
            "publish_profile",
            "lesson_publication_consent",
            "data_privacy_agreement",
            "email",
            "secondary_email",
            "gender",
            "gender_other",
            "country",
            "airport",
            "affiliation",
            "github",
            "twitter",
            "url",
            "occupation",
            "orcid",
            "user_notes",
            "lessons",
            "domains",
            "languages",
        ]

        widgets = {
            "country": Select2Widget,
            "gender": RadioSelectWithOther("gender_other"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self["gender"].field.widget.other_field = self["gender_other"]

        # remove additional fields
        self.helper.layout.fields.remove("gender_other")

    def clean(self):
        super().clean()
        errors = dict()

        # 1: require "other gender" field if "other" was selected in
        # "gender" field
        gender = self.cleaned_data.get("gender", "")
        gender_other = self.cleaned_data.get("gender_other", "")
        if gender == GenderMixin.OTHER and not gender_other:
            errors["gender"] = ValidationError("This field is required.")
        elif gender != GenderMixin.OTHER and gender_other:
            errors["gender"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


class PersonCreateForm(PersonForm):
    comment = MarkdownxFormField(
        label="Comment",
        help_text="This will be added to comments after the person is " "created.",
        widget=forms.Textarea,
        required=False,
    )

    class Meta(PersonForm.Meta):
        # remove 'username' field as it's being populated after form save
        # in the `views.PersonCreate.form_valid`
        fields = PersonForm.Meta.fields.copy()
        fields.remove("username")
        fields.append("comment")


class PersonPermissionsForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    user_permissions = forms.ModelMultipleChoiceField(
        label=Person._meta.get_field("user_permissions").verbose_name,
        help_text=Person._meta.get_field("user_permissions").help_text,
        required=False,
        queryset=Permission.objects.select_related("content_type"),
    )
    user_permissions.widget.attrs.update({"class": "resizable-vertical", "size": "20"})

    class Meta:
        model = Person
        # only display administration-related fields: groups, permissions,
        # being a superuser or being active (== ability to log in)
        fields = [
            "is_active",
            "is_superuser",
            "user_permissions",
            "groups",
        ]


class PersonsSelectionForm(forms.Form):
    person_a = forms.ModelChoiceField(
        label="Person From",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),
    )

    person_b = forms.ModelChoiceField(
        label="Person To",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class PersonsMergeForm(forms.Form):
    TWO = (
        ("obj_a", "Use A"),
        ("obj_b", "Use B"),
    )
    THREE = TWO + (("combine", "Combine"),)
    DEFAULT = "obj_a"

    person_a = forms.ModelChoiceField(
        queryset=Person.objects.all(), widget=forms.HiddenInput
    )

    person_b = forms.ModelChoiceField(
        queryset=Person.objects.all(), widget=forms.HiddenInput
    )

    id = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    username = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    personal = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    middle = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    family = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    email = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    secondary_email = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    may_contact = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    publish_profile = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    data_privacy_agreement = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    gender = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    gender_other = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    airport = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    github = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    twitter = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    url = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    affiliation = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    occupation = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    orcid = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    award_set = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    qualification_set = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
        label="Lessons",
    )
    domains = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    languages = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    task_set = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    is_active = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    trainingprogress_set = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    comment_comments = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    comments = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )


class AwardForm(WidgetOverrideMixin, forms.ModelForm):
    class Meta:
        model = Award
        fields = "__all__"
        widgets = {
            "person": ModelSelect2Widget(
                data_view="person-lookup", attrs=SELECT2_SIDEBAR
            ),
            "event": ModelSelect2Widget(
                data_view="event-lookup", attrs=SELECT2_SIDEBAR
            ),
            "awarded_by": ModelSelect2Widget(
                data_view="admin-lookup", attrs=SELECT2_SIDEBAR
            ),
        }

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        failed_trainings = kwargs.pop("failed_trainings", False)
        super().__init__(*args, **kwargs)
        bootstrap_kwargs = {
            "add_cancel_button": False,
            "form_tag": form_tag,
        }
        if failed_trainings:
            bootstrap_kwargs["submit_onclick"] = (
                'return confirm("Warning: Trainee failed previous training(s).'
                ' Are you sure you want to continue?");'
            )
        self.helper = BootstrapHelper(**bootstrap_kwargs)


class EventLookupForm(forms.Form):
    event = forms.ModelChoiceField(
        label="Event",
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view="event-lookup"),
    )

    helper = BootstrapHelper(add_cancel_button=False)


class PersonLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label="Person",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class AdminLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label="Administrator",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(
            data_view="admin-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )

    helper = BootstrapHelper(add_cancel_button=False)


class EventsSelectionForm(forms.Form):
    event_a = forms.ModelChoiceField(
        label="Event A",
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view="event-lookup"),
    )

    event_b = forms.ModelChoiceField(
        label="Event B",
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view="event-lookup"),
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class EventsMergeForm(forms.Form):
    TWO = (
        ("obj_a", "Use A"),
        ("obj_b", "Use B"),
    )
    THREE = TWO + (("combine", "Combine"),)
    DEFAULT = "obj_a"

    event_a = forms.ModelChoiceField(
        queryset=Event.objects.all(), widget=forms.HiddenInput
    )

    event_b = forms.ModelChoiceField(
        queryset=Event.objects.all(), widget=forms.HiddenInput
    )

    id = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    slug = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    completed = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    assigned_to = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    start = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    end = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    host = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    sponsor = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    administrator = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    public_status = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    tags = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    url = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    language = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    reg_key = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    manual_attendance = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    contact = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    country = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    venue = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    address = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    latitude = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    longitude = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    learners_pre = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    learners_post = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    instructors_pre = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    instructors_post = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    learners_longterm = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    task_set = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    comments = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )


# ----------------------------------------------------------
# Action required forms


class ActionRequiredPrivacyForm(forms.ModelForm):
    data_privacy_agreement = forms.BooleanField(
        label="*I have read and agree to <a href="
        '"https://docs.carpentries.org/topic_folders/policies/privacy.html"'
        ' target="_blank" rel="noreferrer">'
        "the data privacy policy of The Carpentries</a>.",
        required=True,
    )

    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = Person
        fields = [
            "data_privacy_agreement",
            "may_contact",
            "publish_profile",
        ]


# ----------------------------------------------------------
# Signals


@receiver(create_comment_signal, sender=EventForm)
@receiver(create_comment_signal, sender=EventCreateForm)
@receiver(create_comment_signal, sender=PersonCreateForm)
def form_saved_add_comment(sender, **kwargs):
    """A receiver for custom form.save() signal. This is intended to save
    comment, entered as a form field, when creating a new object, and present
    it as automatic system Comment (from django_comments app)."""
    content_object = kwargs.get("content_object", None)
    comment = kwargs.get("comment", None)
    timestamp = kwargs.get("timestamp", datetime.now(timezone.utc))

    # only proceed if we have an actual object (that exists in DB), and
    # comment contents
    if content_object and comment and content_object.pk:
        site = Site.objects.get_current()
        Comment.objects.create(
            content_object=content_object,
            site=site,
            user=None,
            user_name="Automatic comment",
            submit_date=timestamp,
            comment=comment,
        )
