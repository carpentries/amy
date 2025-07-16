from django import forms

from offering.models import Account, AccountBenefit, Benefit


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


class AccountOwnerForm:
    pass


class BenefitForm(forms.ModelForm[Benefit]):
    class Meta:
        model = Benefit
        fields = [
            "active",
            "name",
            "description",
            "unit_type",
        ]


class AccountBenefitForm(forms.ModelForm[AccountBenefit]):
    class Meta:
        model = AccountBenefit
        fields = [
            "account",
            "membership",
            "benefit",
            "curriculum",
            "start_date",
            "end_date",
            "allocation",
        ]
