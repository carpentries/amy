from django import forms
from django.core.exceptions import ValidationError

from communityroles.models import CommunityRole
from workshops.fields import ModelSelect2Widget
from workshops.forms import BootstrapHelper
from workshops.models import Person

from .models import InstructorRecruitment, InstructorRecruitmentSignup


class InstructorRecruitmentCreateForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False, submit_label="Add sign up page")

    class Meta:
        model = InstructorRecruitment
        fields = ("priority", "notes")


class InstructorRecruitmentAddSignupForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    person = forms.ModelChoiceField(
        label="Instructor",
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="instructor-lookup"),
    )

    class Meta:
        model = InstructorRecruitmentSignup
        fields = ("person", "notes")

    def __init__(self, *args, **kwargs):
        self._recruitment = kwargs.pop("recruitment", None)
        super().__init__(*args, **kwargs)

    def clean_person(self) -> None:
        person = self.cleaned_data["person"]

        try:
            (
                CommunityRole.objects.active().get(  # type: ignore
                    person=person, config__name="instructor"
                )
            )
        except CommunityRole.DoesNotExist:
            raise ValidationError(
                f"Person {person} does not have an active Instructor Community Role"
            )

        if (
            self._recruitment
            and self._recruitment.signups.filter(person=person).exists()
        ):
            raise ValidationError(
                f"Person {person} is already signed up for this recruitment"
            )

        return person


class InstructorRecruitmentSignupUpdateForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = InstructorRecruitmentSignup
        fields = ("notes",)


class InstructorRecruitmentSignupChangeStateForm(forms.Form):
    ALLOWED_ACTIONS = (
        ("confirm", "Confirm"),
        ("decline", "Decline"),
    )
    action = forms.ChoiceField(choices=ALLOWED_ACTIONS)


class InstructorRecruitmentChangeStateForm(forms.Form):
    ALLOWED_ACTIONS = (
        ("close", "Close"),
        ("reopen", "Reopen"),
    )
    action = forms.ChoiceField(choices=ALLOWED_ACTIONS)
