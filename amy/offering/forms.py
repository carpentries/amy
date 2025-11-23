from typing import Any

from crispy_forms.layout import Div
from django import forms

from fiscal.forms import EditableFormsetFormMixin
from offering.models import Account, AccountBenefit, AccountOwner, Benefit
from workshops.fields import HeavySelect2Widget, ModelSelect2Widget
from workshops.forms import BootstrapHelper


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
            ),  # type: ignore[no-untyped-call]
        }

    class Media:
        # The order below is important, as `django_select2.js` is being imported by the Select2 widgets, and
        # it may overwrite `.djangoSelect2()` calls in custom JS media files, like `offering_account_form.js` below.
        js = (
            "django_select2/django_select2.js",
            "offering_account_form.js",
        )


class AccountOwnerForm(EditableFormsetFormMixin[AccountOwner], forms.ModelForm[AccountOwner]):
    """Form intended to use in formset for creating multiple account owners."""

    helper = BootstrapHelper(
        add_cancel_button=False,
        form_tag=False,
        add_submit_button=False,
        # formset gathers media, so there's no need to include them in every individual
        # form (plus this prevents an unnecessary bug when multiple handlers are
        # attached to the same element)
        include_media=False,
    )
    helper_deletable = BootstrapHelper(
        add_cancel_button=False,
        form_tag=False,
        add_submit_button=False,
        include_media=False,
    )
    helper_empty_form = BootstrapHelper(add_cancel_button=False, form_tag=False, add_submit_button=False)
    helper_empty_form_deletable = BootstrapHelper(add_cancel_button=False, form_tag=False, add_submit_button=False)

    class Media:
        js = ("accountowner_formset.js",)

    class Meta:
        model = AccountOwner
        fields = [
            # The membership field is required for uniqueness validation. We're making
            # it hidden from user to not confuse them, and to discourage from changing
            # field's value. The downside of this approach is that a) user can provide
            # different ID if they try hard enough, and b) tests get a little bit
            # harder as additional value has to be provided.
            "account",
            "person",
            "permission_type",
        ]
        widgets = {
            "account": forms.HiddenInput,
            "person": ModelSelect2Widget(data_view="person-lookup"),  # type: ignore[no-untyped-call]
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # set up layout objects for the helpers - they're identical except for
        # visibility of the delete checkbox
        self.helper.layout = self.helper.build_default_layout(self)  # type: ignore
        self.helper.layout.append("id")

        self.helper_deletable.layout = self.helper.build_default_layout(self)  # type: ignore
        self.helper_deletable.layout.append("id")
        self.helper_deletable.layout.append("DELETE")  # visible; formset adds it

        self.helper_empty_form.layout = self.helper.build_default_layout(self)  # type: ignore
        self.helper_empty_form.layout.append("id")
        # remove EDITABLE checkbox from empty helper form
        pos_index = self.helper_empty_form.layout.fields.index("EDITABLE")
        self.helper_empty_form.layout.pop(pos_index)

        self.helper_empty_form_deletable.layout = self.helper.build_default_layout(self)  # type: ignore
        self.helper_empty_form_deletable.layout.append("id")
        self.helper_empty_form_deletable.layout.append(Div("DELETE", css_class="d-none"))  # type: ignore
        # remove EDITABLE checkbox from empty helper deletable form
        pos_index = self.helper_empty_form_deletable.layout.fields.index("EDITABLE")
        self.helper_empty_form_deletable.layout.pop(pos_index)


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
            "discount",
            "curriculum",
            "start_date",
            "end_date",
            "allocation",
        ]
