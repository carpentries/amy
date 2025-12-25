from typing import cast

from crispy_forms.layout import Layout
from django import forms
from django.forms import CharField, RadioSelect, TextInput

from src.trainings.models import Involvement
from src.trainings.utils import raise_validation_error_if_no_learner_task

# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from src.workshops.fields import ModelSelect2Widget
from src.workshops.forms import SELECT2_SIDEBAR, BootstrapHelper
from src.workshops.models import Event, Person, TrainingProgress, TrainingRequirement


class TrainingProgressForm(forms.ModelForm[TrainingProgress]):
    trainee = forms.ModelChoiceField(
        label="Trainee",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),  # type: ignore[no-untyped-call]
    )
    requirement = forms.ModelChoiceField(
        queryset=TrainingRequirement.objects.all(),
        label="Type",
        required=True,
    )
    involvement_type = forms.ModelChoiceField(
        label="Get Involved activity",
        required=False,
        queryset=Involvement.objects.default_order().filter(archived_at__isnull=True),
        widget=RadioSelect(),
    )
    event = forms.ModelChoiceField(
        label="Event",
        required=False,
        queryset=Event.objects.all(),
        help_text="If a trainee is selected, only the events for which that trainee has a learner task are listed.",
        widget=ModelSelect2Widget(data_view="ttt-event-lookup", attrs=SELECT2_SIDEBAR),  # type: ignore[no-untyped-call]
    )
    trainee_notes = CharField(
        label="Notes from trainee",
        required=False,
        disabled=True,
    )

    # helper used in edit view
    helper = BootstrapHelper(
        duplicate_buttons_on_top=True,
        submit_label="Update",
        add_delete_button=True,
        additional_form_class="training-progress",
        add_cancel_button=False,
    )

    # helper used in create view
    create_helper = BootstrapHelper(
        duplicate_buttons_on_top=True,
        submit_label="Add",
        additional_form_class="training-progress",
        add_cancel_button=False,
    )

    class Meta:
        model = TrainingProgress
        fields = [
            "trainee",
            "requirement",
            "state",
            "involvement_type",
            "event",
            "url",
            "date",
            "trainee_notes",
            "notes",
        ]
        widgets = {
            "state": RadioSelect,
        }

    class Media:
        js = ("trainingprogress_form.js",)

    def clean_event(self) -> Event:
        trainee = self.cleaned_data["trainee"]
        event = cast(Event, self.cleaned_data["event"])
        raise_validation_error_if_no_learner_task(trainee, event)
        return event


class BulkAddTrainingProgressForm(forms.ModelForm[TrainingProgress]):
    event = forms.ModelChoiceField(
        label="Training",
        required=False,
        queryset=Event.objects.filter(tags__name="TTT"),
        widget=ModelSelect2Widget(data_view="ttt-event-lookup", attrs=SELECT2_SIDEBAR),  # type: ignore[no-untyped-call]
    )

    trainees = forms.ModelMultipleChoiceField(queryset=Person.objects.all())

    requirement = forms.ModelChoiceField(
        queryset=TrainingRequirement.objects.all(),
        label="Type",
        required=True,
    )

    involvement_type = forms.ModelChoiceField(
        label="Type of involvement",
        required=False,
        queryset=Involvement.objects.default_order().filter(archived_at__isnull=True),
        widget=RadioSelect(),
    )

    helper = BootstrapHelper(
        additional_form_class="training-progress",
        submit_label="Add",
        form_tag=False,
        add_cancel_button=False,
    )
    helper.layout = Layout(  # type: ignore[no-untyped-call]
        # no 'trainees' -- you should take care of generating it manually in
        # the template where this form is used
        "requirement",
        "state",
        "involvement_type",
        "event",
        "url",
        "date",
        "notes",
    )

    class Meta:
        model = TrainingProgress
        fields = [
            # no 'trainees'
            "requirement",
            "state",
            "involvement_type",
            "event",
            "url",
            "date",
            "notes",
        ]
        widgets = {
            "state": RadioSelect,
            "notes": TextInput,
        }

    class Media:
        js = ("trainingprogress_form.js",)
