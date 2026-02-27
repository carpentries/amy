from datetime import date, timedelta
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Prefetch, QuerySet
from django.forms import BaseModelFormSet, modelformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from flags.views import FlaggedViewMixin  # type: ignore[import-untyped]

from src.communityroles.models import CommunityRole
from src.emails.actions.exceptions import EmailStrategyException
from src.emails.actions.new_partnership_onboarding import (
    new_partnership_onboarding_strategy,
    run_new_partnership_onboarding_strategy,
)
from src.fiscal.models import Partnership
from src.offering.base_views import AccountFormsetView
from src.offering.filters import AccountBenefitFilter, AccountFilter, BenefitFilter
from src.offering.forms import (
    AccountBenefitForm,
    AccountForm,
    AccountOwnerForm,
    BenefitForm,
)
from src.offering.models import Account, AccountBenefit, AccountOwner, Benefit
from src.workshops.base_forms import GenericDeleteForm
from src.workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYListView,
    AMYUpdateView,
    AuthenticatedHttpRequest,
)
from src.workshops.filters import EventCategoryFilter
from src.workshops.forms import EventCategoryForm
from src.workshops.models import Event, EventCategory, Person, Task
from src.workshops.utils.access import OnlyForAdminsMixin
from src.workshops.utils.urls import safe_next_or_default_url

REQUIRED_FLAG_NAME = "SERVICE_OFFERING"


# -----------------------------------------------------------------


class AccountList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[Account]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_account"]
    template_name = "offering/account_list.html"
    queryset = Account.objects.order_by("-created_at")
    title = "Accounts"
    filter_class = AccountFilter


class AccountDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[Account]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_account"]
    template_name = "offering/account_details.html"
    model = Account

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        context["owners"] = AccountOwner.objects.filter(account=self.object).select_related("person")
        context["account_benefits"] = (
            AccountBenefit.objects.filter(account=self.object)
            .select_related("benefit")
            .prefetch_related(
                Prefetch("event_set", queryset=Event.objects.select_related("host")),
                Prefetch("task_set", queryset=Task.objects.select_related("event", "person", "role")),
            )
        )
        if self.object.account_type != "individual":
            context["partnerships"] = (
                Partnership.objects.credits_usage_annotation()
                .filter(account=self.object)
                .select_related("tier", "partner_consortium", "partner_organisation", "account")
            )
            context["community_roles"] = CommunityRole.objects.filter(partnership__account=self.object).select_related(
                "partnership", "person"
            )
        return context


class AccountCreate(OnlyForAdminsMixin, FlaggedViewMixin, AMYCreateView[AccountForm, Account]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.add_account"]
    template_name = "offering/account_create.html"
    form_class = AccountForm
    model = Account
    object: Account
    title = "Create a new account"

    def form_valid(self, form: AccountForm) -> HttpResponse:
        obj = form.save(commit=False)
        obj.generic_relation_content_type = Account.get_content_type_for_account_type(
            form.cleaned_data["account_type"],
        )
        obj.save()

        if obj.account_type == Account.AccountTypeChoices.INDIVIDUAL:
            # Automatically create an AccountOwner for individual accounts. It's the same as the person
            # this account is for.
            try:
                owner = Person.objects.get(pk=form.cleaned_data["generic_relation_pk"])
                AccountOwner.objects.create(
                    account=obj,
                    person=owner,
                    permission_type=AccountOwner.PERMISSION_TYPE_CHOICES[0][0],
                )
            except Person.DoesNotExist:
                pass

        return super().form_valid(form)


class AccountUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView[AccountForm, Account]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_account", "offering.change_account"]
    template_name = "offering/account_edit.html"
    form_class = AccountForm
    model = Account
    object: Account

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context

    def form_valid(self, form: AccountForm) -> HttpResponse:
        obj = form.save(commit=False)
        # Update content type in case account type was changed
        obj.generic_relation_content_type = Account.get_content_type_for_account_type(
            form.cleaned_data["account_type"],
        )
        obj.save()

        if obj.account_type == Account.AccountTypeChoices.INDIVIDUAL:
            # Update AccountOwner for individual accounts. It's the same as the person this account is for.
            try:
                owner = Person.objects.get(pk=form.cleaned_data["generic_relation_pk"])
                AccountOwner.objects.update_or_create(
                    account=obj,
                    permission_type=AccountOwner.PERMISSION_TYPE_CHOICES[0][0],
                    defaults=dict(person=owner),
                    create_defaults=dict(
                        person=owner,
                        permission_type=AccountOwner.PERMISSION_TYPE_CHOICES[0][0],
                    ),
                )
            except Person.DoesNotExist:
                pass

        return super().form_valid(form)


class AccountDelete(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYDeleteView[Account, GenericDeleteForm[Account]],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.delete_account"]
    model = Account

    def get_success_url(self) -> str:
        return reverse("account-list")


# -----------------------------------------------------------------


class AccountOwnersUpdate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    PermissionRequiredMixin,
    AccountFormsetView[AccountOwner, AccountOwnerForm],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = [
        "offering.change_account",
        "offering.add_accountowner",
        "offering.change_accountowner",
        "offering.delete_accountowner",
    ]
    request: AuthenticatedHttpRequest

    def account_queryset_kwargs(self) -> dict[str, Any]:
        # Prevent from loading the page for account type of "individual"
        return dict(account_type__in=[Account.AccountTypeChoices.CONSORTIUM, Account.AccountTypeChoices.ORGANISATION])

    def get_formset(self, *args: Any, **kwargs: Any) -> type[BaseModelFormSet[AccountOwner, AccountOwnerForm]]:
        return modelformset_factory(AccountOwner, AccountOwnerForm, *args, **kwargs)

    def get_formset_queryset(self, object: Account) -> QuerySet[AccountOwner]:
        return object.accountowner_set.select_related("account", "person")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if "title" not in kwargs:
            kwargs["title"] = f"Change owners for {self.account}"
        return super().get_context_data(**kwargs)

    def form_valid(self, formset: BaseModelFormSet[AccountOwner, AccountOwnerForm]) -> HttpResponse:
        result = super().form_valid(formset)

        for partnership in Partnership.objects.filter(account=self.account):
            try:
                run_new_partnership_onboarding_strategy(
                    new_partnership_onboarding_strategy(partnership),
                    request=self.request,
                    partnership=partnership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )

        return result


# -----------------------------------------------------------------


class BenefitList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[Benefit]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_benefit"]
    template_name = "offering/benefit_list.html"
    queryset = Benefit.objects.order_by("-created_at")
    title = "Benefits"
    filter_class = BenefitFilter


class BenefitDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[Benefit]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_benefit"]
    template_name = "offering/benefit_details.html"
    model = Benefit

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class BenefitCreate(OnlyForAdminsMixin, FlaggedViewMixin, AMYCreateView[BenefitForm, Benefit]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.add_benefit"]
    template_name = "offering/benefit_create.html"
    form_class = BenefitForm
    model = Benefit
    object: Benefit
    title = "Create a new benefit"


class BenefitUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView[BenefitForm, Benefit]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_benefit", "offering.change_benefit"]
    template_name = "offering/benefit_edit.html"
    form_class = BenefitForm
    model = Benefit
    object: Benefit

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class BenefitDelete(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYDeleteView[Benefit, GenericDeleteForm[Benefit]],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.delete_benefit"]
    model = Benefit

    def get_success_url(self) -> str:
        return reverse("benefit-list")


# -----------------------------------------------------------------


class AccountBenefitList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[AccountBenefit]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_accountbenefit"]
    template_name = "offering/account_benefit_list.html"
    queryset = AccountBenefit.objects.order_by("-created_at")
    title = "Account Benefits"
    filter_class = AccountBenefitFilter


class AccountBenefitDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[AccountBenefit]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_accountbenefit"]
    template_name = "offering/account_benefit_details.html"
    model = AccountBenefit

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        context["tasks"] = Task.objects.filter(allocated_benefit=self.object).select_related("event", "person", "role")
        context["events"] = Event.objects.filter(allocated_benefit=self.object).select_related("host")
        return context


class AccountBenefitCreate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYCreateView[AccountBenefitForm, AccountBenefit],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.add_accountbenefit"]
    template_name = "offering/account_benefit_create.html"
    form_class = AccountBenefitForm
    model = AccountBenefit
    object: AccountBenefit
    title = "Create a new account benefit"

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial["start_date"] = date.today()
        initial["end_date"] = date.today() + timedelta(days=365)

        if account_pk := self.request.GET.get("account_pk"):
            initial["account"] = get_object_or_404(Account, pk=account_pk)

        if partnership_pk := self.request.GET.get("partnership_pk"):
            partnership = get_object_or_404(Partnership, pk=partnership_pk)
            initial["partnership"] = partnership
            initial["start_date"] = partnership.agreement_start
            initial["end_date"] = partnership.agreement_end

        return initial

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()

        if (account := kwargs.get("initial", {}).get("account")) is not None:
            kwargs["disable_account"] = True
            if account.account_type == Account.AccountTypeChoices.INDIVIDUAL:
                # For individual accounts, we also disable partnership selection
                kwargs["disable_partnership"] = True

        if kwargs.get("initial", {}).get("partnership") is not None:
            kwargs["disable_partnership"] = True
            kwargs["disable_dates"] = True

        return kwargs

    def get_success_url(self) -> str:
        default_url = super().get_success_url()
        return safe_next_or_default_url(self.request.GET.get("next"), default_url)


class AccountBenefitUpdate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYUpdateView[AccountBenefitForm, AccountBenefit],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_accountbenefit", "offering.change_accountbenefit"]
    template_name = "offering/account_benefit_edit.html"
    form_class = AccountBenefitForm
    model = AccountBenefit
    object: AccountBenefit

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class AccountBenefitDelete(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYDeleteView[AccountBenefit, GenericDeleteForm[AccountBenefit]],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.delete_accountbenefit"]
    model = AccountBenefit

    def get_success_url(self) -> str:
        return reverse("account-benefit-list")


# -----------------------------------------------------------------


class EventCategoryList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[EventCategory]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_eventcategory"]
    template_name = "offering/event_category_list.html"
    queryset = EventCategory.objects.order_by("name")
    title = "Event Categories"
    filter_class = EventCategoryFilter


class EventCategoryDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[EventCategory]):  # type: ignore[misc]
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_eventcategory"]
    template_name = "offering/event_category_details.html"
    model = EventCategory

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f'Event Category "{self.object}"'
        return context


class EventCategoryCreate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYCreateView[EventCategoryForm, EventCategory],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.add_eventcategory"]
    template_name = "offering/event_category_create.html"
    form_class = EventCategoryForm
    model = EventCategory
    object: EventCategory
    title = "Create a new event category"


class EventCategoryUpdate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYUpdateView[EventCategoryForm, EventCategory],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.view_eventcategory", "offering.change_eventcategory"]
    template_name = "offering/event_category_edit.html"
    form_class = EventCategoryForm
    model = EventCategory
    object: EventCategory

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f'Event Category "{self.object}"'
        return context


class EventCategoryDelete(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYDeleteView[EventCategory, GenericDeleteForm[EventCategory]],
):
    flag_name = REQUIRED_FLAG_NAME
    permission_required = ["offering.delete_eventcategory"]
    model = EventCategory

    def get_success_url(self) -> str:
        return reverse("event-category-list")
