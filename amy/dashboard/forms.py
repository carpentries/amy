from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django_countries.fields import CountryField

from communityroles.models import CommunityRole
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from trainings.models import Involvement
from workshops.fields import (
    AirportChoiceField,
    ModelSelect2MultipleWidget,
    RadioSelectWithOther,
    Select2Widget,
    TimezoneChoiceField,
)
from workshops.forms import BootstrapHelper
from workshops.mixins import GenderMixin
from workshops.models import (
    Event,
    Language,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)


class AssignmentForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        label="Assigned to:",
        required=False,
        queryset=Person.objects.filter(Q(is_superuser=True) | Q(groups__name="administrators")).distinct(),
        widget=Select2Widget(),
    )
    helper = BootstrapHelper(
        add_submit_button=False,
        add_cancel_button=False,
        wider_labels=True,
        use_get_method=True,
        form_id="assignment-form",
    )


class AutoUpdateProfileForm(forms.ModelForm[Person]):
    username = forms.CharField(disabled=True, required=False)
    email = forms.CharField(
        disabled=True,
        required=False,
        label=Person._meta.get_field("email").verbose_name,
        help_text=Person._meta.get_field("email").help_text,
    )
    github = forms.CharField(
        disabled=True,
        required=False,
        help_text="If you want to change your github username, please email "
        'us at <a href="mailto:team@carpentries.org">'
        "team@carpentries.org</a>.",
    )

    airport_iata = AirportChoiceField(
        required=True, label="Airport", help_text="Country and timezone of the airport are in the parentheses."
    )
    country = CountryField().formfield(
        required=False,
        help_text="Override country of the airport.",
        widget=Select2Widget,
    )  # type: ignore
    timezone = TimezoneChoiceField(required=False, help_text="Override timezone of the airport.")

    languages = forms.ModelMultipleChoiceField(
        label="Languages",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2MultipleWidget(data_view="language-lookup"),  # type: ignore[no-untyped-call]
    )

    class Meta:
        model = Person
        fields = [
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
            "github",
            "twitter",
            "bluesky",
            "mastodon",
            "url",
            "username",
            "affiliation",
            "domains",
            "lessons",
            "languages",
            "occupation",
            "orcid",
        ]
        readonly_fields = (
            "username",
            "github",
        )
        widgets = {
            "gender": RadioSelectWithOther("gender_other"),
            "domains": forms.CheckboxSelectMultiple(),
            "lessons": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        form_tag = kwargs.pop("form_tag", True)
        add_submit_button = kwargs.pop("add_submit_button", True)
        super().__init__(*args, **kwargs)
        self.helper = BootstrapHelper(
            add_cancel_button=False,
            form_tag=form_tag,
            add_submit_button=add_submit_button,
        )

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
            errors["gender"] = ValidationError('If you entered data in "Other" field, please select that ' "option.")

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


class GetInvolvedForm(forms.ModelForm[TrainingProgress]):
    """Trainee-facing form for submitting training progress.

    All fields have required=False to prevent confusion, as required fields change
    based on the involvement choice.
    """

    involvement_type = forms.ModelChoiceField[Involvement](
        label="Activity",
        help_text="If your activity is not included in this list, please select "
        '"Other" and provide details under "Additional information" below.',
        required=False,
        queryset=Involvement.objects.default_order().filter(archived_at__isnull=True),
        widget=forms.RadioSelect(),
    )
    date = forms.DateField(
        label="Date of activity",
        help_text="If the activity took place over multiple days, please enter the " "first day. Format: YYYY-MM-DD",
        required=False,
    )
    url = forms.URLField(
        label="URL",
        help_text="A link to the activity, if there is one. If you served "
        "at a workshop, enter the workshop website. "
        "If you made a GitHub contribution, enter that link and ensure it is to a"
        "Carpentries GitHub repository (not a fork).",
        required=False,
    )
    trainee_notes = forms.CharField(
        label="Additional information",
        help_text="If you attended a community meeting, please tell us which meeting "
        'you attended. If you selected "Other" for the activity, please '
        "provide details here.",
        required=False,
    )
    helper = BootstrapHelper(add_cancel_button=True)

    CARPENTRIES_GITHUB_ORGS = [
        "carpentries",
        "datacarpentry",
        "LibraryCarpentry",
        "swcarpentry",
        "carpentries-es",
        "Reproducible-Science-Curriculum",
        "CarpentryCon",
        "CarpentryConnect",
        "carpentries-workshops",
        "data-lessons",
        "carpentries-lab",
        "carpentries-incubator",
        "carpentrieslab",
    ]

    class Meta:
        model = TrainingProgress
        fields = [
            "involvement_type",
            "date",
            "url",
            "trainee_notes",
        ]

    def user_may_create_submission(self, user: Person) -> bool:
        """The user may create a submission if either of the conditions below are met:
        1. no progress exists for the Get Involved step for this user
        2. all existing progress for the Get Involved step for this user has state "a"
        """
        get_involved = TrainingRequirement.objects.get(name="Get Involved")
        existing_progresses = TrainingProgress.objects.filter(requirement=get_involved, trainee=user)
        num_existing = existing_progresses.count()
        if num_existing == 0:
            return True
        else:
            num_asked_to_repeat = existing_progresses.filter(state="a").count()
            if num_asked_to_repeat == num_existing:
                return True
            else:
                return False

    def clean_url(self) -> str:
        """Check if URL is associated with a Carpentries GitHub organisation"""
        involvement_type = self.cleaned_data["involvement_type"]
        url = cast(str, self.cleaned_data["url"])
        if involvement_type and involvement_type.name == "GitHub Contribution":
            if not url:
                # This check is part of model validation, but form validation runs
                # first. As an empty URL will trigger the next error, first replicate
                # the "URL required" error check here for this specific Involvement.
                msg = "This field is required for activity " f'"{involvement_type.display_name}".'
                raise ValidationError(msg)
            else:
                case_insensitive_url = url.casefold()
                if not any(
                    f"github.com/{org}".casefold() in case_insensitive_url for org in self.CARPENTRIES_GITHUB_ORGS
                ):
                    msg = (
                        "This URL is not associated with a repository in any of the "
                        "GitHub organisations owned by The Carpentries. "
                        "If you need help resolving this error, please contact us "
                        "using the details at the top of this form."
                    )
                    raise ValidationError(msg)

        return url

    def clean_trainee_notes(self) -> str:
        """Raise an error if the trainee has not provided notes where required.

        All other fields are cleaned in the TrainingProgress model itself.
        This field is different as it should only show an error on this specific form.
        """
        involvement_type = self.cleaned_data["involvement_type"]
        trainee_notes = cast(str, self.cleaned_data["trainee_notes"])
        if involvement_type and involvement_type.notes_required and not trainee_notes:
            raise ValidationError(f'This field is required for activity "{involvement_type}".')

        return trainee_notes

    def clean(self) -> None:
        super().clean()

        # check that the user may create/update this TrainingProgress instance
        if self.instance:
            if self.instance.pk is None and not self.user_may_create_submission(self.instance.trainee):
                raise ValidationError(
                    "You already have an existing submission. "
                    "You may not create another submission unless your previous "
                    'submission has the status "asked to repeat."'
                )
            elif self.instance.pk and self.instance.state != "n":
                raise ValidationError("This submission can no longer be edited as it has already been " "evaluated.")


class SearchForm(forms.Form):
    """Represent general searching form."""

    term = forms.CharField(label="Term", max_length=100)
    no_redirect = forms.BooleanField(required=False, initial=False)
    helper = BootstrapHelper(add_cancel_button=False, use_get_method=True)


class SignupForRecruitmentForm(forms.ModelForm[InstructorRecruitmentSignup]):
    user_notes = forms.CharField(
        required=False,
        widget=forms.Textarea,
        label="Your notes",
        help_text="Is there anything else you would like to share with us? "
        "Please include any accommodations that the host organization should provide "
        "to enable you to teach effectively.",
    )
    helper = BootstrapHelper(
        submit_label="Submit my interest in teaching this workshop",
        add_cancel_button=False,
    )

    class Meta:
        model = InstructorRecruitmentSignup
        fields = [
            "user_notes",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.person: Person = kwargs.pop("person")
        self.recruitment: InstructorRecruitment = kwargs.pop("recruitment")
        super().__init__(*args, **kwargs)

    def clean(self) -> None:
        super().clean()

        try:
            (CommunityRole.objects.active().get(person=self.person, config__name="instructor"))
        except CommunityRole.DoesNotExist:
            raise ValidationError("You don't have an active Instructor Community Role")

        signups_exist = self.recruitment.signups.filter(person=self.person).exists()
        if signups_exist:
            raise ValidationError("You are already signed up for this recruitment")

        # Check if user has any instructor roles for events taking place at the same
        # time of this event.
        event: Event = self.recruitment.event
        if (
            event.start
            and event.end
            and (
                conflicting_tasks := Task.objects.filter(
                    person=self.person,
                    role__name="instructor",
                    event__start__lte=event.end,
                    event__end__gte=event.start,
                )
            )
        ):
            # error not bound to any particular field
            raise ValidationError(
                "Selected event dates conflict with events: "
                f"{', '.join(task.event.slug for task in conflicting_tasks)}"
            )
