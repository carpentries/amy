import re
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any, cast

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Div, Field, Layout, Submit
from django import forms
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.dispatch import receiver
from django.forms import CheckboxSelectMultiple, Form, SelectMultiple, TextInput
from django_comments.models import Comment
from django_countries import Countries
from django_countries.fields import CountryField
from markdownx.fields import MarkdownxFormField

from src.communityroles.models import CommunityRole
from src.dashboard.models import Continent

# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from src.workshops.fields import (
    HeavySelect2Widget,
    ModelSelect2MultipleWidget,
    ModelSelect2Widget,
    RadioSelectWithOther,
    Select2MultipleWidget,
    Select2TagWidget,
    Select2Widget,
    TimezoneChoiceField,
)
from src.workshops.mixins import GenderMixin
from src.workshops.models import (
    Award,
    Badge,
    Curriculum,
    Event,
    EventCategory,
    KnowledgeDomain,
    Language,
    Lesson,
    Membership,
    Organization,
    Person,
    Role,
    Tag,
    Task,
)
from src.workshops.signals import create_comment_signal

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
        form: Form | None = None,
        duplicate_buttons_on_top: bool = False,
        submit_label: str = "Submit",
        submit_name: str = "submit",
        submit_onclick: str | None = None,
        use_get_method: bool = False,
        wider_labels: bool = False,
        add_submit_button: bool = True,
        add_delete_button: bool = False,
        add_cancel_button: bool = True,
        additional_form_class: str = "",
        form_tag: bool = True,
        display_labels: bool = True,
        form_action: str | None = None,
        form_id: str | None = None,
        include_media: bool = True,
    ) -> None:
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

        super().__init__(form)  # type: ignore

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
            self.add_input(  # type: ignore
                Submit(
                    submit_name,
                    submit_label,
                    onclick=submit_onclick,
                )  # type: ignore
            )

        if add_delete_button:
            self.add_input(  # type: ignore
                Submit(
                    "delete",
                    "Delete",
                    onclick='return confirm("Are you sure you want to delete it?");',
                    form="delete-form",
                    css_class="btn-danger float-right",
                )  # type: ignore
            )

        if add_cancel_button:
            self.add_input(  # type: ignore
                Button(
                    "cancel",
                    "Cancel",
                    css_class="btn-secondary float-right",
                    onclick="window.history.back()",
                )  # type: ignore
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

    def hr(self) -> str:
        """Horizontal line as a separator in forms is used very often. But
        since from time to time the forms are changed (in terms of columns
        width), we should rather use one global <hr>..."""
        return '<hr class="col-12 mx-0 px-0">'


class BootstrapHelperFilter(FormHelper):
    """A differently shaped forms (more space-efficient) for use in sidebar as
    filter forms."""

    form_method = "get"
    form_id = "filter-form"

    def __init__(self, form: Form | None = None) -> None:
        super().__init__(form)  # type: ignore
        self.attrs["role"] = "form"
        self.inputs.append(
            Submit("", "Submit"),  # type: ignore
        )


class BootstrapHelperFormsetInline(BootstrapHelper):
    """For use in inline formsets."""

    template = "bootstrap/table_inline_formset.html"  # type: ignore


bootstrap_helper_filter = BootstrapHelperFilter()
bootstrap_helper_inline_formsets = BootstrapHelperFormsetInline()


# ----------------------------------------------------------
# MixIns


class PrivacyConsentMixin(forms.Form):
    privacy_consent = forms.BooleanField(
        label="*I have read and agree to <a href="
        '"https://docs.carpentries.org/policies/privacy.html"'
        ' target="_blank" rel="noreferrer">'
        "the data privacy policy of The Carpentries</a>.",
        required=True,
    )


class WidgetOverrideMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        widgets = kwargs.pop("widgets", {})
        super().__init__(*args, **kwargs)
        for field, widget in widgets.items():
            self.fields[field].widget = widget  # type: ignore


# ----------------------------------------------------------
# Forms


def continent_list() -> list[tuple[str | int, str]]:
    """This has to be as a callable, because otherwise Django evaluates this
    query and, if the database doesn't exist yet (e.g. during Travis-CI
    tests)."""
    return [("", "")] + list(Continent.objects.values_list("pk", "name"))


class WorkshopStaffForm(forms.Form):
    """Represent instructor matching form."""

    latitude = forms.FloatField(label="Latitude", min_value=-90.0, max_value=90.0, required=False)
    longitude = forms.FloatField(label="Longitude", min_value=-180.0, max_value=180.0, required=False)
    airport_iata = forms.CharField(
        required=False,
        label="Airport",
        widget=HeavySelect2Widget(data_view="airports-lookup"),  # type: ignore[no-untyped-call]
    )
    languages = forms.ModelMultipleChoiceField(
        label="Languages",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2MultipleWidget(  # type: ignore[no-untyped-call]
            data_view="language-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )
    domains = forms.ModelMultipleChoiceField(
        label="Knowlege Domains",
        required=False,
        queryset=KnowledgeDomain.objects.all(),
        widget=ModelSelect2MultipleWidget(  # type: ignore[no-untyped-call]
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

    is_instructor = forms.BooleanField(required=False, label="Has active Instructor Community Role")
    is_trainer = forms.BooleanField(required=False, label="Has Trainer badge")

    GENDER_CHOICES = ((None, "---------"),) + Person.GENDER_CHOICES
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)

    was_helper = forms.BooleanField(required=False, label="Was helper at least once before")
    was_organizer = forms.BooleanField(required=False, label="Was organizer at least once before")
    is_in_progress_trainee = forms.BooleanField(required=False, label="Is an in-progress instructor trainee")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Build form layout dynamically."""
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)  # type: ignore
        self.helper.form_method = "get"
        self.helper.layout = Layout(  # type: ignore
            Div(  # type: ignore
                Div(  # type: ignore
                    HTML('<h5 class="card-title">Location</h5>'),  # type: ignore
                    "airport_iata",
                    HTML("<hr>"),  # type: ignore
                    "country",
                    HTML("<hr>"),  # type: ignore
                    "continent",
                    HTML("<hr>"),  # type: ignore
                    "latitude",
                    "longitude",
                    css_class="card-body",
                ),
                css_class="card",
            ),
            "is_instructor",
            "is_trainer",
            HTML("<hr>"),  # type: ignore
            "was_helper",
            "was_organizer",
            "is_in_progress_trainee",
            "languages",
            "domains",
            "gender",
            "lessons",
            Submit("", "Submit"),  # type: ignore
        )

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = cast(dict[str, Any], super().clean())
        lat = bool(cleaned_data.get("latitude"))
        lng = bool(cleaned_data.get("longitude"))
        airport_iata = bool(cleaned_data.get("airport_iata"))
        country = bool(cleaned_data.get("country"))
        latlng = lat and lng

        # if searching by coordinates, then there must be both lat & lng
        # present
        if lat ^ lng:
            raise ValidationError("Must specify both latitude and longitude if searching by coordinates")

        # User must search by airport, or country, or coordinates, or none
        # of them. Sum of boolean elements must be equal 0 (if general search)
        # or 1 (if searching by airport OR country OR lat/lng).
        if sum([airport_iata, country, latlng]) not in [0, 1]:
            raise ValidationError("Must specify an airport OR a country, OR use coordinates, OR none of them.")
        return cleaned_data


class BulkUploadCSVForm(forms.Form):
    """This form allows to upload a single file; it's used by person bulk
    upload and training request manual score bulk upload."""

    file = forms.FileField()


class EventForm(forms.ModelForm[Event]):
    host = forms.ModelChoiceField(
        label="Host Site",
        required=True,
        help_text=Event._meta.get_field("host").help_text,
        queryset=Organization.objects.all(),
        widget=ModelSelect2Widget(data_view="organization-lookup"),  # type: ignore[no-untyped-call]
    )

    sponsor = forms.ModelChoiceField(
        label="Organiser",
        required=True,
        help_text=Event._meta.get_field("sponsor").help_text,
        queryset=Organization.objects.all(),
        widget=ModelSelect2Widget(data_view="organization-lookup"),  # type: ignore[no-untyped-call]
    )

    administrator = forms.ModelChoiceField(
        label="Administrator",
        required=True,
        help_text=Event._meta.get_field("administrator").help_text,
        queryset=Organization.objects.administrators(),
        widget=ModelSelect2Widget(data_view="administrator-org-lookup"),  # type: ignore[no-untyped-call]
    )

    assigned_to = forms.ModelChoiceField(
        label="Assigned to",
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="admin-lookup"),  # type: ignore[no-untyped-call]
    )

    language = forms.ModelChoiceField(
        label="Language",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2Widget(data_view="language-lookup"),  # type: ignore[no-untyped-call]
    )

    country = CountryField().formfield(
        required=False,
        help_text=Event._meta.get_field("country").help_text,
        widget=Select2Widget,
    )  # type: ignore

    comment = MarkdownxFormField(
        label="Comment",
        help_text="Any content in here will be added to comments after this event is saved.",
        widget=forms.Textarea,
        required=False,
    )  # type: ignore

    instructors_pre = forms.URLField(
        label="Assessment survey for instructors:",
        help_text=("Auto-generated as long as the event is NOT marked as complete and it has a slug."),
        required=False,
        assume_scheme="https",
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
            "membership",
            "allocated_benefit",
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
            "event_category",
            "curricula",
            "lessons",
            "public_status",
            "instructors_pre",
            "comment",
        ]
        widgets = {
            "membership": ModelSelect2Widget(data_view="membership-lookup"),  # type: ignore[no-untyped-call]
            "allocated_benefit": ModelSelect2Widget(data_view="account-benefit-events-lookup"),  # type: ignore[no-untyped-call]
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        show_lessons = kwargs.pop("show_lessons", False)
        add_comment = kwargs.pop("add_comment", True)
        show_allocated_benefit = kwargs.pop("show_allocated_benefit", False)
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(  # type: ignore
            Field("slug", placeholder="YYYY-MM-DD-location"),  # type: ignore
            "completed",
            Field("start", placeholder="YYYY-MM-DD"),  # type: ignore
            Field("end", placeholder="YYYY-MM-DD"),  # type: ignore
            "host",
            "sponsor",
            "membership",
            "allocated_benefit" if show_allocated_benefit else None,
            "administrator",
            "public_status",
            "assigned_to",
            "event_category",
            "curricula",
            "tags",
            "open_TTT_applications",
            "url",
            "language",
            "reg_key",
            "manual_attendance",
            "contact",
            "instructors_pre",
            Div(  # type: ignore
                Div(HTML("Location details"), css_class="card-header"),  # type: ignore
                Div(  # type: ignore
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

    def clean_slug(self) -> str:
        # Ensure slug is in "YYYY-MM-DD-location" format
        data = cast(str, self.cleaned_data["slug"])
        match = re.match(r"(\d{4}|x{4})-(\d{2}|x{2})-(\d{2}|x{2})-.+", data)
        if not match:
            raise ValidationError(
                'Slug must be in "YYYY-MM-DD-location" format, where "YYYY", "MM", "DD" can be unspecified (ie. "xx").'
            )
        return data

    def clean_end(self) -> date:
        """Ensure end >= start."""
        start = cast(date, self.cleaned_data["start"])
        end = cast(date, self.cleaned_data["end"])

        if start and end and end < start:
            raise ValidationError("Must not be earlier than start date.")
        return end

    def clean_open_TTT_applications(self) -> bool:
        """Ensure there's a TTT tag applied to the event, if the
        `open_TTT_applications` is True."""
        open_TTT_applications = cast(bool, self.cleaned_data["open_TTT_applications"])
        tags = cast(QuerySet[Tag] | None, self.cleaned_data.get("tags", None))
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

    def get_missing_tags(self) -> set[str]:
        """Validate tags when some curricula are selected.

        Called during clean(), not during individual field validation."""
        curricula = cast(QuerySet[Curriculum], self.cleaned_data["curricula"])
        tags = cast(QuerySet[Tag], self.cleaned_data["tags"])
        try:
            expected_tags = set()
            for c in curricula:
                if c.active and c.carpentry:
                    expected_tags.add(c.carpentry)
                elif c.active and c.mix_match:
                    expected_tags.add("Circuits")
        except (ValueError, TypeError):
            expected_tags = set()

        missing_tags = expected_tags - set(tags.values_list("name", flat=True))
        return missing_tags

    def clean_manual_attendance(self) -> int:
        """Regression: #1608 - fix 500 server error when field is cleared."""
        manual_attendance = cast(int | None, self.cleaned_data["manual_attendance"]) or 0
        return manual_attendance

    def save(self, *args: Any, **kwargs: Any) -> Event:
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

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        if not cleaned_data:
            return cleaned_data

        errors: defaultdict[str, list[ValidationError]] = defaultdict(list)

        if missing_tags := self.get_missing_tags():
            errors["tags"].append(
                ValidationError(
                    "You must add tags corresponding to the selected curricula. "
                    f"Missing tags: {', '.join(missing_tags)}"
                ),
            )

        if cleaned_data["allocated_benefit"] and cleaned_data["membership"]:
            errors["allocated_benefit"].append(
                ValidationError("You cannot have both allocated benefit and membership for the same event."),
            )

        if errors:
            raise ValidationError(errors)

        return cleaned_data


class EventCreateForm(EventForm):
    comment = MarkdownxFormField(
        label="Comment",
        help_text="This will be added to comments after the event is created.",
        widget=forms.Textarea,
        required=False,
    )  # type: ignore


class EventCategoryForm(forms.ModelForm[EventCategory]):
    class Meta:
        model = EventCategory
        fields = [
            "name",
            "description",
            "active",
        ]


class TaskForm(WidgetOverrideMixin, forms.ModelForm[Task]):
    SEAT_MEMBERSHIP_HELP_TEXT = (
        "{}<br><b>Hint:</b> you can use input format YYYY-MM-DD to display memberships available on that date.".format(
            Task._meta.get_field("seat_membership").help_text
        )
    )
    seat_membership = forms.ModelChoiceField(
        label=Task._meta.get_field("seat_membership").verbose_name,
        help_text=SEAT_MEMBERSHIP_HELP_TEXT,
        required=False,
        queryset=Membership.objects.all(),
        widget=ModelSelect2Widget(  # type: ignore[no-untyped-call]
            data_view="membership-lookup-for-tasks",
            attrs=SELECT2_SIDEBAR,
        ),
    )

    class Meta:
        model = Task
        fields = [
            "event",
            "person",
            "role",
            "seat_membership",
            # "seat_public",
            # "seat_open_training",
            "allocated_benefit",
        ]
        widgets = {
            "person": ModelSelect2Widget(data_view="person-lookup", attrs=SELECT2_SIDEBAR),  # type: ignore
            "event": ModelSelect2Widget(data_view="event-lookup", attrs=SELECT2_SIDEBAR),  # type: ignore
            "allocated_benefit": ModelSelect2Widget(data_view="account-benefit-seats-lookup", attrs=SELECT2_SIDEBAR),  # type: ignore[no-untyped-call]
            # "seat_public": forms.RadioSelect(),
        }

    class Media:
        js = ("task_form.js",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        form_tag = kwargs.pop("form_tag", True)
        failed_trainings = kwargs.pop("failed_trainings", False)
        show_allocated_benefit = kwargs.pop("show_allocated_benefit", False)
        super().__init__(*args, **kwargs)
        bootstrap_kwargs = {
            "add_cancel_button": False,
            "form_tag": form_tag,
        }
        if failed_trainings:
            bootstrap_kwargs["submit_onclick"] = (
                'return confirm("Warning: Trainee failed previous training(s). Are you sure you want to continue?");'
            )
        self.helper = BootstrapHelper(**bootstrap_kwargs)
        self.helper.layout = Layout(  # type: ignore
            "event",
            "person",
            "role",
            "seat_membership",
            # "seat_public",
            # "seat_open_training",
            "allocated_benefit" if show_allocated_benefit else None,
        )

    def clean(self) -> dict[str, Any] | None:
        result = super().clean()
        errors = dict()
        person: Person = self.cleaned_data["person"]
        role: Role = self.cleaned_data["role"]
        event: Event = self.cleaned_data["event"]

        # Check validity of person's community role
        if role.name == "instructor":
            # If event is TTT (Train The Trainers), then community role "trainer"
            # corresponds to role "instructor"; otherwise it's "instructor" community
            # role.
            community_role_name = "instructor"
            if event.administrator and event.administrator.domain == "carpentries.org":
                community_role_name = "trainer"

            person_community_roles = CommunityRole.objects.filter(
                person=person, config__name__iexact=community_role_name
            ).select_related("config")

            no_active_role = not any(role.is_active() for role in person_community_roles)

            if person_community_roles and no_active_role:
                errors["role"] = ValidationError(
                    f'{person} has inactive "{community_role_name}" community role(s) related to "{{role.name}}" task.'
                )

        if self.cleaned_data["allocated_benefit"] and self.cleaned_data["seat_membership"]:
            errors["allocated_benefit"] = ValidationError(
                "You cannot have both allocated benefit and membership for the same event."
            )

        # raise errors if any present
        if errors:
            raise ValidationError(errors)

        return result


class PersonForm(forms.ModelForm[Person]):
    airport_iata = forms.CharField(
        required=True,
        label="Airport",
        help_text="Country and timezone of the airport are in the parentheses.",
        widget=HeavySelect2Widget(data_view="airports-lookup"),  # type: ignore[no-untyped-call]
    )
    timezone = TimezoneChoiceField(required=False, help_text="Override timezone of the airport.")
    languages = forms.ModelMultipleChoiceField(
        label="Languages",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2MultipleWidget(data_view="language-lookup"),  # type: ignore[no-untyped-call]
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
            "email",
            "secondary_email",
            "gender",
            "gender_other",
            "airport_iata",
            "country",
            "timezone",
            "affiliation",
            "github",
            "twitter",
            "bluesky",
            "mastodon",
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)  # type: ignore

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self["gender"].field.widget.other_field = self["gender_other"]

        # remove additional fields
        self.helper.layout.fields.remove("gender_other")

    def clean(self) -> None:
        super().clean()
        errors = dict()

        # 1: require "other gender" field if "other" was selected in
        # "gender" field
        gender = self.cleaned_data.get("gender", "")
        gender_other = self.cleaned_data.get("gender_other", "")
        if gender == GenderMixin.OTHER and not gender_other:
            errors["gender"] = ValidationError("This field is required.")
        elif gender != GenderMixin.OTHER and gender_other:
            errors["gender"] = ValidationError('If you entered data in "Other" field, please select that option.')

        # raise errors if any present
        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> Person:
        if "airport_iata" in self.changed_data:
            self.instance.country = ""
            self.instance.timezone = ""
        return super().save(*args, **kwargs)


class PersonCreateForm(PersonForm):
    comment = MarkdownxFormField(
        label="Comment",
        help_text="This will be added to comments after the person is created.",
        widget=forms.Textarea,
        required=False,
    )  # type: ignore

    class Meta(PersonForm.Meta):
        # remove 'username' field as it's being populated after form save
        # in the `views.PersonCreate.form_valid`
        fields = PersonForm.Meta.fields.copy()
        fields.remove("username")
        fields.append("comment")


class PersonPermissionsForm(forms.ModelForm[Person]):
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
        widget=ModelSelect2Widget(data_view="person-lookup"),  # type: ignore[no-untyped-call]
    )

    person_b = forms.ModelChoiceField(
        label="Person To",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),  # type: ignore[no-untyped-call]
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class PersonsMergeForm(forms.Form):
    TWO = (
        ("obj_a", "Use A"),
        ("obj_b", "Use B"),
    )
    THREE = TWO + (("combine", "Combine"),)
    DEFAULT = "obj_a"

    person_a = forms.ModelChoiceField(queryset=Person.objects.all(), widget=forms.HiddenInput)

    person_b = forms.ModelChoiceField(queryset=Person.objects.all(), widget=forms.HiddenInput)

    id = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    username = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    personal = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    middle = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    family = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    email = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    secondary_email = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    gender = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    gender_other = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    airport_iata = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    country = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    timezone = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    github = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    twitter = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    bluesky = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    mastodon = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    url = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    affiliation = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    occupation = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    orcid = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    award_set = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    qualification_set = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect, label="Lessons")
    domains = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    languages = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    task_set = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    is_active = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    trainingprogress_set = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    comment_comments = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    comments = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    consent_set = forms.ChoiceField(
        choices=(("most_recent", "Use the most recent consents"),), initial="most_recent", widget=forms.RadioSelect
    )


class AwardForm(WidgetOverrideMixin, forms.ModelForm[Award]):
    badge = forms.ModelChoiceField(
        queryset=Badge.objects.exclude(name__in=["lc-instructor", "dc-instructor", "swc-instructor"]).order_by(
            "title", "name"
        ),
        label="Badge",
        required=True,
    )

    class Meta:
        model = Award
        fields = "__all__"
        widgets = {
            "person": ModelSelect2Widget(data_view="person-lookup", attrs=SELECT2_SIDEBAR),  # type: ignore
            "event": ModelSelect2Widget(data_view="event-lookup-for-awards", attrs=SELECT2_SIDEBAR),  # type: ignore
            "awarded_by": ModelSelect2Widget(data_view="admin-lookup", attrs=SELECT2_SIDEBAR),  # type: ignore
        }

    class Media:
        js = ("award_form.js",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        form_tag = kwargs.pop("form_tag", True)
        failed_trainings = kwargs.pop("failed_trainings", False)
        super().__init__(*args, **kwargs)
        bootstrap_kwargs = {
            "add_cancel_button": False,
            "form_tag": form_tag,
        }
        if failed_trainings:
            bootstrap_kwargs["submit_onclick"] = (
                'return confirm("Warning: Trainee failed previous training(s). Are you sure you want to continue?");'
            )
        self.helper = BootstrapHelper(**bootstrap_kwargs)


class EventLookupForm(forms.Form):
    event = forms.ModelChoiceField(
        label="Event",
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view="event-lookup"),  # type: ignore[no-untyped-call]
    )

    helper = BootstrapHelper(add_cancel_button=False)


class PersonLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label="Person",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),  # type: ignore[no-untyped-call]
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class AdminLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label="Administrator",
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(  # type: ignore[no-untyped-call]
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
        widget=ModelSelect2Widget(data_view="event-lookup"),  # type: ignore[no-untyped-call]
    )

    event_b = forms.ModelChoiceField(
        label="Event B",
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view="event-lookup"),  # type: ignore[no-untyped-call]
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class EventsMergeForm(forms.Form):
    TWO = (
        ("obj_a", "Use A"),
        ("obj_b", "Use B"),
    )
    THREE = TWO + (("combine", "Combine"),)
    DEFAULT = "obj_a"

    event_a = forms.ModelChoiceField(queryset=Event.objects.all(), widget=forms.HiddenInput)

    event_b = forms.ModelChoiceField(queryset=Event.objects.all(), widget=forms.HiddenInput)

    id = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    slug = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    completed = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    assigned_to = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    start = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    end = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    host = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect, label="Host Site")
    sponsor = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect, label="Organiser")
    administrator = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    public_status = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    tags = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    url = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    language = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    reg_key = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    manual_attendance = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    contact = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    country = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    venue = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    address = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    latitude = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    longitude = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    learners_pre = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    learners_post = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    instructors_pre = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    instructors_post = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    learners_longterm = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    open_TTT_applications = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    curricula = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    lessons = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    public_status = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    event_category = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    task_set = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)
    comments = forms.ChoiceField(choices=THREE, initial=DEFAULT, widget=forms.RadioSelect)


# ----------------------------------------------------------
# Signals


@receiver(create_comment_signal, sender=EventForm)
@receiver(create_comment_signal, sender=EventCreateForm)
@receiver(create_comment_signal, sender=PersonCreateForm)
def form_saved_add_comment(sender: Any, **kwargs: Any) -> None:
    """A receiver for custom form.save() signal. This is intended to save
    comment, entered as a form field, when creating a new object, and present
    it as automatic system Comment (from django_comments app)."""
    content_object = kwargs.get("content_object")
    comment = kwargs.get("comment")
    timestamp = kwargs.get("timestamp", datetime.now(UTC))

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
