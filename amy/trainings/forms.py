from crispy_forms.layout import Layout
from django import forms
from django.core.exceptions import ValidationError
from django.forms import RadioSelect, TextInput

from trainings.models import Involvement

# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import ModelSelect2Widget, RadioSelectWithOther
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
        widget=RadioSelectWithOther("involvement_other"),
    )
    event = forms.ModelChoiceField(
        label="Event",
        required=False,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view="event-lookup", attrs=SELECT2_SIDEBAR),
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
            "involvement_other",
            "event",
            "url",
            "date",
            "notes",
        ]
        widgets = {
            "state": RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up layout objects for the helpers
        self.helper.layout = self.helper.build_default_layout(self)
        self.create_helper.layout = self.create_helper.build_default_layout(self)

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self["involvement_type"].field.widget.other_field = self["involvement_other"]

        # remove additional fields
        self.helper.layout.fields.remove("involvement_other")
        self.create_helper.layout.fields.remove("involvement_other")

    def clean(self):
        cleaned_data = super().clean()

        trainee = cleaned_data.get("trainee")

        # check if trainee has at least one training task
        training_tasks = trainee.get_training_tasks()

        if not training_tasks:
            raise ValidationError(
                "It's not possible to add training progress "
                "to a trainee without any training task."
            )

        errors = dict()

        # TODO: validation based on url_required in Involvement, etc

        # 1: require "other involvement" field if "other" was selected in
        # "involvement type" field
        involvement = self.cleaned_data.get("involvement_type", "")
        involvement_other = self.cleaned_data.get("involvement_other", "")
        if involvement.name == "Other" and not involvement_other:
            errors["involvement"] = ValidationError("This field is required.")
        elif involvement.name != "Other" and involvement_other:
            errors["involvement"] = ValidationError(
                'If you entered data in "Other" field, please select that option.'
            )

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


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
        "event",
        "url",
        "notes",
    )

    class Meta:
        model = TrainingProgress
        fields = [
            # no 'trainees'
            "requirement",
            "state",
            "event",
            "url",
            "notes",
        ]
        widgets = {
            "state": RadioSelect,
            "notes": TextInput,
        }

    def clean(self):
        cleaned_data = super().clean()

        trainees = cleaned_data.get("trainees", [])

        # check if all trainees have at least one training task
        for trainee in trainees:
            training_tasks = trainee.get_training_tasks()

            if not training_tasks:
                raise ValidationError(
                    "It's not possible to add training "
                    "progress to a trainee without any "
                    "training task."
                )
