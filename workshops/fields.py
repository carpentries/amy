from dal_select2.widgets import (
    Select2WidgetMixin as DALSelect2WidgetMixin,
)
from dal.autocomplete import (
    Select2 as DALSelect2,
    Select2Multiple as DALSelect2Multiple,
    ListSelect2 as DALListSelect2,
    ModelSelect2 as DALModelSelect2,
    ModelSelect2Multiple as DALModelSelect2Multiple,
    TagSelect2 as DALTagSelect2,
)
from django.core.validators import RegexValidator, MaxLengthValidator
from django.db import models
from django import forms


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
# "Rewrite" select2 widgets from Django Autocomplete Light so
# that they don't use Django's admin-provided jQuery, which
# causes errors with jQuery provided by us.

class Select2WidgetMixin(DALSelect2WidgetMixin):
    @property
    def media(self):
        m = super().media
        js = list(m._js)
        try:
            js.remove('admin/js/vendor/jquery/jquery.js')
            js.remove('admin/js/vendor/jquery/jquery.min.js')
        except ValueError:
            pass
        return forms.Media(css=m._css, js=js)

class Select2(Select2WidgetMixin, DALSelect2):
    pass

class Select2Multiple(Select2WidgetMixin, DALSelect2Multiple):
    pass

class ListSelect2(Select2WidgetMixin, DALListSelect2):
    pass

class ModelSelect2(Select2WidgetMixin, DALModelSelect2):
    pass

class ModelSelect2Multiple(Select2WidgetMixin, DALModelSelect2Multiple):
    pass

class TagSelect2(Select2WidgetMixin, DALTagSelect2):
    pass
