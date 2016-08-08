from django import forms

from workshops.forms import TaskFullForm, SponsorshipForm, BootstrapHelper
from workshops.models import Person, Task, Sponsorship


class PersonMinimalForm(forms.ModelForm):

    class Meta:
        model = Person
        fields = ('username', 'personal', 'family', 'email', 'url')


class BaseModelAddFormSet(forms.models.BaseModelFormSet):
    can_delete = True
    can_order = False
    min_num = forms.formsets.DEFAULT_MIN_NUM
    max_num = forms.formsets.DEFAULT_MAX_NUM
    absolute_max = 2 * max_num
    validate_max = False
    validate_min = False

    helper = BootstrapHelper(form_tag=False, add_submit_button=False)

    def __init__(self, *args, **kwargs):
        # Override the default form helper
        super().__init__(*args, **kwargs)
        self.form.helper = self.helper

    def add_fields(self, form, index):
        # Change label of DELETE checkbox
        super().add_fields(form, index)
        form[forms.formsets.DELETION_FIELD_NAME].label = 'Do not import'

    def get_queryset(self):
        # Do not show any existing model in the formset
        return self.model.objects.none()

    def total_form_count(self):
        # Restrict the total number of forms to number of initial forms
        if self.data or self.files:
            return super().total_form_count()
        else:
            return len(self.initial_extra)


class PersonAddFormSet(BaseModelAddFormSet):
    model = Person
    form = PersonMinimalForm


class TaskAddFormSet(BaseModelAddFormSet):
    model = Task
    form = TaskFullForm


class SponsorshipAddFormSet(BaseModelAddFormSet):
    model = Sponsorship
    form = SponsorshipForm
