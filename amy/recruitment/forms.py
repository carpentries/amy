from django import forms

from workshops.forms import BootstrapHelper

from .models import InstructorRecruitment


class InstructorRecruitmentCreateForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False, submit_label="Add sign up page")

    class Meta:
        model = InstructorRecruitment
        fields = ("notes",)


class InstructorRecruitmentSignupChangeStateForm(forms.Form):
    ALLOWED_ACTIONS = (
        ("confirm", "Confirm"),
        ("decline", "Decline"),
    )
    action = forms.ChoiceField(choices=ALLOWED_ACTIONS)
