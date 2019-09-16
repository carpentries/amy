from django_select2.forms import (
    Select2Widget as DS2_Select2Widget,
    Select2MultipleWidget as DS2_Select2MultipleWidget,
    ModelSelect2Widget as DS2_ModelSelect2Widget,
    ModelSelect2MultipleWidget as DS2_ModelSelect2MultipleWidget,
    Select2TagWidget as DS2_Select2TagWidget,
)
from django.core.validators import RegexValidator, MaxLengthValidator
from django.db import models
from django import forms
from django.utils.safestring import mark_safe


GHUSERNAME_MAX_LENGTH_VALIDATOR = MaxLengthValidator(39,
    message='Maximum allowed username length is 39 characters.',
)
# according to https://stackoverflow.com/q/30281026,
# GH username can only contain alphanumeric characters and
# hyphens (but not consecutive), cannot start or end with
# a hyphen, and can't be longer than 39 characters
GHUSERNAME_REGEX_VALIDATOR = RegexValidator(
    # regex inspired by above StackOverflow thread
    regex=r'^([a-zA-Z\d](?:-?[a-zA-Z\d])*)$',
    message='This is not a valid GitHub username.',
)


class NullableGithubUsernameField(models.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('default', '')
        # max length of the GH username is 39 characters
        kwargs.setdefault('max_length', 39)
        super().__init__(**kwargs)

    default_validators = [
        GHUSERNAME_MAX_LENGTH_VALIDATOR,
        GHUSERNAME_REGEX_VALIDATOR,
    ]


#------------------------------------------------------------

class FakeRequiredMixin:
    def __init__(self, *args, **kwargs):
        # Intercept "fake_required" attribute that's used for marking field
        # with "*" (asterisk) even though it's not required.
        # Additionally `fake_required` doesn't trigger any validation.
        self.fake_required = kwargs.pop('fake_required', False)
        super().__init__(*args, **kwargs)


class RadioSelectWithOther(FakeRequiredMixin, forms.RadioSelect):
    """A RadioSelect widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


class CheckboxSelectMultipleWithOthers(FakeRequiredMixin, forms.CheckboxSelectMultiple):
    """A multiple choice widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


class RadioSelectFakeMultiple(FakeRequiredMixin, forms.RadioSelect):
    """Pretend to be a radio-select with multiple selection possible. This
    is intended to 'fool' Django into thinking that user selected 1 item on
    a multi-select item list."""
    allow_multiple_selected = True


class SafeLabelFromInstanceMixin:
    def label_from_instance(self, obj):
        return mark_safe(obj)


class SafeModelChoiceField(SafeLabelFromInstanceMixin, forms.ModelChoiceField):
    pass


class SafeModelMultipleChoiceField(SafeLabelFromInstanceMixin,
                                   forms.ModelMultipleChoiceField):
    pass


class CurriculumModelMultipleChoiceField(SafeModelMultipleChoiceField):
    def label_from_instance(self, obj):
        # Display in tooltip (it's a little better than popover, because it
        # auto-hides and doesn't require clicking on the element, whereas
        # popover by clicking will automatically select the clicked item)
        data = (
            '<a tabindex="0" role="button" data-toggle="tooltip" '
            'data-placement="top" title="{description}">{obj}</a>'
            .format(obj=obj, description=obj.description)
        )
        return super().label_from_instance(data)


#------------------------------------------------------------

class Select2BootstrapMixin:
    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs.setdefault('data-theme', 'bootstrap4')
        return attrs


class Select2NoMinimumInputLength:
    def build_attrs(self, *args, **kwargs):
        # Let's set up the minimum input length first!
        # It will overwrite `setdefault('data-minimum-input-length')` from
        # other mixins.
        self.attrs.setdefault('data-minimum-input-length', 0)
        attrs = super().build_attrs(*args, **kwargs)
        return attrs



class Select2Widget(FakeRequiredMixin, Select2BootstrapMixin,
                    DS2_Select2Widget):
    pass


class Select2MultipleWidget(Select2BootstrapMixin, DS2_Select2MultipleWidget):
    pass


class ModelSelect2Widget(Select2BootstrapMixin, Select2NoMinimumInputLength,
                         DS2_ModelSelect2Widget):
    pass


class ModelSelect2MultipleWidget(Select2BootstrapMixin,
                                 Select2NoMinimumInputLength,
                                 DS2_ModelSelect2MultipleWidget):
    pass


class Select2TagWidget(Select2BootstrapMixin, DS2_Select2TagWidget):
    def value_from_datadict(self, data, files, name):
        # sometimes data is held as an immutable QueryDict
        # in those cases, we need to make a copy of it to "disable"
        # the mutability
        try:
            data_mutable = data.copy()
        except AttributeError:
            data_mutable = data

        data_mutable.setdefault(name, '')
        return super().value_from_datadict(data_mutable, files, name)
