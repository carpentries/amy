from django import forms

from offering.models import Account, Benefit, EventCategory


class AccountForm(forms.ModelForm[Account]):
    class Meta:
        model = Account
        fields = [
            "active",
            "account_type",
            "generic_relation_content_type",
            "generic_relation_pk",
        ]
        # TODO: select2 for selecting specific relation object


class BenefitForm(forms.ModelForm[Benefit]):
    class Meta:
        model = Benefit
        fields = [
            "active",
            "account",
            "event_category",
            "membership",
            "curriculum",
            "start_date",
            "end_date",
            "allocation",
        ]


class EventCategoryForm(forms.ModelForm[EventCategory]):
    class Meta:
        model = EventCategory
        fields = [
            "active",
            "name",
            "description",
        ]
