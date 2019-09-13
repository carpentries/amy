from crispy_forms.layout import Layout, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.forms import (
    TextInput,
    RadioSelect,
)

from workshops.forms import (
    SELECT2_SIDEBAR,
    BootstrapHelper,
)
from workshops.models import (
    Event,
    Person,
    TrainingProgress,
)
# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import (
    ModelSelect2Widget,
)


class TrainingProgressForm(forms.ModelForm):
    trainee = forms.ModelChoiceField(
        label='Trainee',
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view='person-lookup')
    )
    evaluated_by = forms.ModelChoiceField(
        label='Evaluated by',
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view='admin-lookup')
    )
    event = forms.ModelChoiceField(
        label='Event',
        required=False,
        queryset=Event.objects.all(),
        widget=ModelSelect2Widget(data_view='event-lookup',
                                  attrs=SELECT2_SIDEBAR)
    )

    # helper used in edit view
    helper = BootstrapHelper(duplicate_buttons_on_top=True,
                             submit_label='Update',
                             add_delete_button=True,
                             additional_form_class='training-progress',
                             add_cancel_button=False)

    # helper used in create view
    create_helper = BootstrapHelper(duplicate_buttons_on_top=True,
                                    submit_label='Add',
                                    additional_form_class='training-progress',
                                    add_cancel_button=False)

    class Meta:
        model = TrainingProgress
        fields = [
            'trainee',
            'evaluated_by',
            'requirement',
            'state',
            'discarded',
            'event',
            'url',
            'notes',
        ]
        widgets = {
            'state': RadioSelect,
        }

    def clean(self):
        cleaned_data = super().clean()

        trainee = cleaned_data.get('trainee')

        # check if trainee has at least one training task
        training_tasks = trainee.get_training_tasks()

        if not training_tasks:
            raise ValidationError("It's not possible to add training progress "
                                  "to a trainee without any training task.")


class BulkAddTrainingProgressForm(forms.ModelForm):
    event = forms.ModelChoiceField(
        label='Training',
        required=False,
        queryset=Event.objects.filter(tags__name='TTT'),
        widget=ModelSelect2Widget(data_view='ttt-event-lookup',
                                  attrs=SELECT2_SIDEBAR)
    )

    trainees = forms.ModelMultipleChoiceField(queryset=Person.objects.all())

    helper = BootstrapHelper(additional_form_class='training-progress',
                             submit_label='Add',
                             form_tag=False,
                             add_cancel_button=False)
    helper.layout = Layout(
        # no 'trainees' -- you should take care of generating it manually in
        # the template where this form is used

        'requirement',
        'state',
        'event',
        'url',
        'notes',
    )

    class Meta:
        model = TrainingProgress
        fields = [
            # no 'trainees'
            'requirement',
            'state',
            'event',
            'url',
            'notes',
        ]
        widgets = {
            'state': RadioSelect,
            'notes': TextInput,
        }

    def clean(self):
        cleaned_data = super().clean()

        trainees = cleaned_data.get('trainees')

        # check if all trainees have at least one training task
        for trainee in trainees:
            training_tasks = trainee.get_training_tasks()

            if not training_tasks:
                raise ValidationError("It's not possible to add training "
                                      "progress to a trainee without any "
                                      "training task.")


class BulkDiscardProgressesForm(forms.Form):
    """Form used to bulk discard all TrainingProgresses associated with
    selected trainees."""

    trainees = forms.ModelMultipleChoiceField(queryset=Person.objects.all())

    helper = BootstrapHelper(add_submit_button=False,
                             form_tag=False,
                             display_labels=False,
                             add_cancel_button=False)

    SUBMIT_POPOVER = '''<p>Discarded progress will be displayed in the following
    way: <span class='badge badge-dark'><strike>Discarded</strike></span>.</p>

    <p>If you want to permanently remove records from system,
    click one of the progress labels and, then, click "delete" button.</p>'''

    helper.layout = Layout(
        # no 'trainees' -- you should take care of generating it manually in
        # the template where this form is used

        # We use formnovalidate on submit button to disable browser
        # validation. This is necessary because this form is used along with
        # BulkAddTrainingProgressForm, which have required fields. Both forms
        # live inside the same <form> tag. Without this attribute, when you
        # click the following submit button, the browser reports missing
        # values in required fields in BulkAddTrainingProgressForm.
        Submit('discard',
               'Discard all progress of selected trainees',
               formnovalidate='formnovalidate',
               **{
                   'data-toggle': 'popover',
                   'data-trigger': 'hover',
                   'data-html': 'true',
                   'data-content': SUBMIT_POPOVER,
                   'css_class': 'btn btn-warning',
               }),
    )
