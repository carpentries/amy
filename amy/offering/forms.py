from django import forms

from offering.models import Account, AccountBenefit, Benefit
from workshops.fields import HeavySelect2Widget


class AccountForm(forms.ModelForm[Account]):
    class Meta:
        model = Account
        fields = [
            "account_type",
            "generic_relation_pk",
            "active",
        ]
        widgets = {
            "generic_relation_pk": HeavySelect2Widget(
                data_view="offering-account-relation-lookup",
            ),
        }

    class Media:
        # The order below is important, as `django_select2.js` is being imported by the Select2 widgets, and
        # it may overwrite `.djangoSelect2()` calls in custom JS media files, like `offering_account_form.js` below.
        js = (
            "django_select2/django_select2.js",
            "offering_account_form.js",
        )


class AccountOwnerForm:
    pass


class BenefitForm(forms.ModelForm[Benefit]):
    class Meta:
        model = Benefit
        fields = [
            "name",
            "description",
            "unit_type",
            "credits",
            "active",
        ]


class AccountBenefitForm(forms.ModelForm[AccountBenefit]):
    class Meta:
        model = AccountBenefit
        fields = [
            "account",
            "partnership",
            "benefit",
            "curriculum",
            "start_date",
            "end_date",
            "allocation",
        ]
