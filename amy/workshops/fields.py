from typing import Any, Mapping, Protocol, Sequence, cast

from django import forms
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.utils.safestring import SafeString, mark_safe
from django_select2.forms import (
    ModelSelect2MultipleWidget as DS2_ModelSelect2MultipleWidget,
)
from django_select2.forms import HeavySelect2Widget as DS2_HeavySelect2Widget
from django_select2.forms import ModelSelect2Widget as DS2_ModelSelect2Widget
from django_select2.forms import Select2MultipleWidget as DS2_Select2MultipleWidget
from django_select2.forms import Select2TagWidget as DS2_Select2TagWidget
from django_select2.forms import Select2Widget as DS2_Select2Widget

from workshops.consts import IATA_AIRPORTS, STR_LONG, STR_MED

GHUSERNAME_MAX_LENGTH_VALIDATOR = MaxLengthValidator(
    39,
    message="Maximum allowed username length is 39 characters.",
)
# according to https://stackoverflow.com/q/30281026,
# GH username can only contain alphanumeric characters and
# hyphens (but not consecutive), cannot start or end with
# a hyphen, and can't be longer than 39 characters
GHUSERNAME_REGEX_VALIDATOR = RegexValidator(
    # regex inspired by above StackOverflow thread
    regex=r"^([a-zA-Z\d](?:-?[a-zA-Z\d])*)$",
    message="This is not a valid GitHub username.",
)


class NullableGithubUsernameField(models.CharField):  # type: ignore
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("default", "")
        # max length of the GH username is 39 characters
        kwargs.setdefault("max_length", 39)
        super().__init__(**kwargs)

    default_validators = [
        GHUSERNAME_MAX_LENGTH_VALIDATOR,
        GHUSERNAME_REGEX_VALIDATOR,
    ]


# ------------------------------------------------------------


class FakeRequiredMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Intercept "fake_required" attribute that's used for marking field
        # with "*" (asterisk) even though it's not required.
        # Additionally `fake_required` doesn't trigger any validation.
        self.fake_required = kwargs.pop("fake_required", False)
        super().__init__(*args, **kwargs)


class RadioSelectWithOther(FakeRequiredMixin, forms.RadioSelect):
    """A RadioSelect widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


class CheckboxSelectMultipleWithOthers(FakeRequiredMixin, forms.CheckboxSelectMultiple):
    """A multiple choice widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


class RadioSelectFakeMultiple(FakeRequiredMixin, forms.RadioSelect):
    """Pretend to be a radio-select with multiple selection possible. This
    is intended to 'fool' Django into thinking that user selected 1 item on
    a multi-select item list."""

    allow_multiple_selected = True


class SafeLabelFromInstanceMixin:
    def label_from_instance(self, obj: Any) -> SafeString:
        return cast(SafeString, mark_safe(obj))


class SafeModelChoiceField(
    SafeLabelFromInstanceMixin,
    forms.ModelChoiceField,  # type: ignore[type-arg]
):
    pass


class SafeModelMultipleChoiceField(
    SafeLabelFromInstanceMixin,
    forms.ModelMultipleChoiceField,  # type: ignore[type-arg]
):
    pass


class CurriculumLikeObj(Protocol):
    description: str

    def __str__(self) -> str: ...


class CurriculumModelMultipleChoiceField(SafeModelMultipleChoiceField):
    def label_from_instance(self, obj: CurriculumLikeObj) -> SafeString:
        # Display in tooltip (it's a little better than popover, because it
        # auto-hides and doesn't require clicking on the element, whereas
        # popover by clicking will automatically select the clicked item)
        data = (
            '<a tabindex="0" role="button" data-toggle="tooltip" '
            'data-placement="top" title="{description}">{obj}</a>'.format(obj=obj, description=obj.description)
        )
        return super().label_from_instance(data)


# ------------------------------------------------------------


class Select2BootstrapMixin:
    def build_attrs(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.attrs.setdefault("data-theme", "bootstrap4")  # type: ignore
        attrs = cast(dict[str, Any], super().build_attrs(*args, **kwargs))  # type: ignore
        return attrs


class Select2NoMinimumInputLength:
    def build_attrs(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        # Let's set up the minimum input length first!
        # It will overwrite `setdefault('data-minimum-input-length')` from
        # other mixins.
        self.attrs.setdefault("data-minimum-input-length", 0)  # type: ignore
        attrs = cast(dict[str, Any], super().build_attrs(*args, **kwargs))  # type: ignore
        return attrs


class Select2Widget(FakeRequiredMixin, Select2BootstrapMixin, DS2_Select2Widget):  # type: ignore
    pass


class Select2MultipleWidget(Select2BootstrapMixin, DS2_Select2MultipleWidget):  # type: ignore
    pass


class ModelSelect2Widget(Select2BootstrapMixin, Select2NoMinimumInputLength, DS2_ModelSelect2Widget):  # type: ignore
    pass


class ModelSelect2MultipleWidget(  # type: ignore[misc,override]
    Select2BootstrapMixin,
    Select2NoMinimumInputLength,
    DS2_ModelSelect2MultipleWidget,
):
    pass


TAG_SEPARATOR = ";"


class Select2TagWidget(Select2BootstrapMixin, DS2_Select2TagWidget):  # type: ignore[misc]
    def build_attrs(self, base_attrs: dict[str, Any], extra_attrs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Select2's tag attributes. By default other token separators are
        used, but we want to use "," and ";"."""
        default_attrs = {
            "data-minimum-input-length": 1,
            "data-tags": "true",
            "data-token-separators": '[",", ";"]',
        }

        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def value_from_datadict(self, data: Mapping[str, Any], files: Any, name: str) -> Any:
        # sometimes data is held as an immutable QueryDict
        # in those cases, we need to make a copy of it to "disable"
        # the mutability
        try:
            data_mutable = data.copy()  # type: ignore[attr-defined]
        except AttributeError:
            data_mutable = data

        data_mutable.setdefault(name, "")
        values = super().value_from_datadict(data_mutable, files, name)
        return TAG_SEPARATOR.join(values)

    def optgroups(
        self, name: str, value: list[str], attrs: dict[str, Any] | None = None
    ) -> list[tuple[str | None, list[dict[str, Any]], int | None]]:
        """Example from
        https://django-select2.readthedocs.io/en/latest/django_select2.html#django_select2.forms.Select2TagWidget
        """  # noqa
        try:
            values = value[0].split(TAG_SEPARATOR)
        except (IndexError, AttributeError):
            values = []

        selected = set(values)
        subgroup = [self.create_option(name, v, v, bool(selected), i) for i, v in enumerate(values)]
        return [(None, subgroup, 0)]


class HeavySelect2Widget(Select2BootstrapMixin, Select2NoMinimumInputLength, DS2_HeavySelect2Widget):  # type: ignore
    pass


def choice_field_with_other(
    choices: Sequence[tuple[str, str]], default: str, verbose_name: str | None = None, help_text: str = ""
) -> tuple[models.CharField, models.CharField]:  # type: ignore
    assert default in [c[0] for c in choices]
    assert all(c[0] != "" for c in choices)

    field = models.CharField(  # type: ignore
        max_length=STR_MED,
        choices=choices,
        verbose_name=verbose_name,
        help_text=help_text,
        null=False,
        blank=False,
        default=default,
    )
    other_field = models.CharField(  # type: ignore
        max_length=STR_LONG,
        verbose_name=" ",
        null=False,
        blank=True,
        default="",
    )
    return field, other_field


class AirportChoiceField(forms.ChoiceField):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        choices = kwargs.pop(
            "choices", sorted([(key, f"{key}: {value["name"]}") for key, value in IATA_AIRPORTS.items()])
        )
        widget = kwargs.pop("widget", Select2Widget)

        super().__init__(*args, **kwargs, choices=choices, widget=widget)
