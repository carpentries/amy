from django import forms

from offering.models import EventCategory


class EventCategoryForm(forms.ModelForm[EventCategory]):
    class Meta:
        model = EventCategory
        fields = [
            "name",
            "description",
        ]
