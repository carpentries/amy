from django import forms

from offering.models import Account, EventCategory


class AccountForm(forms.ModelForm[Account]):
    class Meta:
        model = Account
        fields = [
            "account_type",
            "generic_relation_content_type",
            "generic_relation_pk",
        ]
        # TODO: select2 for selecting specific relation object


class EventCategoryForm(forms.ModelForm[EventCategory]):
    class Meta:
        model = EventCategory
        fields = [
            "name",
            "description",
        ]
