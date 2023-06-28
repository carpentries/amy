from crispy_forms.layout import Layout
from django import forms
from django.core.exceptions import ValidationError
from django.forms import CharField, RadioSelect, TextInput

from trainings.models import Involvement

# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import ModelSelect2Widget
from workshops.forms import SELECT2_SIDEBAR, BootstrapHelper
from workshops.models import Event, Person, TrainingProgress, TrainingRequirement


class TrainingProgressForm(forms.ModelForm):
    trainee = forms.ModelChoiceField(
        label="Trainee",
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),
    )
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
    event = forms.ModelChoiceField(
        label="Event",
        required=False,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view="event-lookup", attrs=SELECT2_SIDEBAR),
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

    def add_error(self, field: str, error: ValidationError | str):
        """Overrides add_error to ignore any errors that are intended to appear
        on the trainee-only "trainee_notes" field."""
        if field == "trainee_notes":
            return
        elif hasattr(error, "error_dict") and "trainee_notes" in error.error_dict:
            error.error_dict.pop("trainee_notes")

        super().add_error(field, error)


class BulkAddTrainingProgressForm(forms.ModelForm):
    event = forms.ModelChoiceField(
        label="Training",
        required=False,
        queryset=Event.objects.filter(tags__name="TTT"),
        widget=ModelSelect2Widget(data_view="ttt-event-lookup", attrs=SELECT2_SIDEBAR),
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
    helper.layout = Layout(
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
