from typing import TypeVar

from django import forms
from django.db.models import Model

_M = TypeVar("_M", bound=Model)


class GenericDeleteForm(forms.ModelForm[_M]):
    pass
