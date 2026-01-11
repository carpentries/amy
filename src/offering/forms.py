from typing import Any, cast

from crispy_forms.layout import Div
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from src.fiscal.forms import EditableFormsetFormMixin
from src.offering.models import Account, AccountBenefit, AccountOwner, Benefit
from src.workshops.fields import HeavySelect2Widget, ModelSelect2Widget
from src.workshops.forms import BootstrapHelper


class AccountForm(forms.ModelForm[Account]):
    class Meta:
        model = Account
        fields = [
            "account_type",
            "generic_relation_pk",
            "active",
        ]
        labels = {
            "generic_relation_pk": "Name",
        }
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        update = "instance" in kwargs and kwargs["instance"] and kwargs["instance"].pk is not None

        if update:
            self.helper = BootstrapHelper(
                submit_label="Update",
                submit_onclick='return confirm("Are you sure you want to update this account?");',
            )

    def clean(self) -> dict[str, Any]:
        cleaned_data = cast(dict[str, Any], super().clean())
        errors = {}

        # Select proper content type based on account type
        account_type = cleaned_data["account_type"]
        generic_relation_content_type = Account.get_content_type_for_account_type(account_type)

        # Verify if there isn't already an account with the given generic relation
        generic_relation_pk = cleaned_data["generic_relation_pk"]
        try:
            account = Account.objects.get(
                generic_relation_content_type=generic_relation_content_type,
                generic_relation_pk=generic_relation_pk,
            )
            errors["generic_relation_pk"] = ValidationError(
                format_html(
                    'An account for the selected entity already exists: <a href="{}">account</a>.',
                    account.get_absolute_url(),
                )
            )
        except Account.DoesNotExist:
            pass

        if errors:
            raise ValidationError(errors)

        return cleaned_data


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
        widgets = {
            "partnership": ModelSelect2Widget(data_view="partnership-lookup"),  # type: ignore[no-untyped-call]
        }

    class Media:
        js = ("offering_account_benefit_for_partnership_form.js",)

    def __init__(
        self,
        *args: Any,
        disable_account: bool = False,
        disable_partnership: bool = False,
        disable_dates: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        if disable_account:
            self.fields["account"].disabled = True
        if disable_partnership:
            self.fields["partnership"].disabled = True
        if disable_dates:
            self.fields["start_date"].disabled = True
            self.fields["end_date"].disabled = True

        # If these fields are disabled, the browser won't send their values and this trips the validation
        # (unless we make them not required).
        self.fields["start_date"].required = False
        self.fields["end_date"].required = False

    def clean(self) -> dict[str, Any]:
        cleaned_data = cast(dict[str, Any], super().clean())
        errors = {}

        # Verify if partnership belongs to the account
        account = cleaned_data["account"]
        partnership = cleaned_data["partnership"]
        if partnership and partnership.account != account:
            errors["partnership"] = ValidationError("Selected partnership does not belong to the selected account.")

        # Set start/end dates from partnership if partnership is set
        if partnership:
            cleaned_data["start_date"] = partnership.agreement_start
            cleaned_data["end_date"] = partnership.agreement_end

        # Ensure start_date and end_date are set
        if not cleaned_data["start_date"]:
            errors["start_date"] = ValidationError("Start date is required.")
        if not cleaned_data["end_date"]:
            errors["end_date"] = ValidationError("End date is required.")

        if (
            (start_date := cleaned_data["start_date"])
            and (end_date := cleaned_data["end_date"])
            and start_date > end_date
        ):
            errors["end_date"] = ValidationError("End date must be after start date.")

        if errors:
            raise ValidationError(errors)

        return cleaned_data
