from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.urls import reverse
from flags.views import FlaggedViewMixin

from offering.filters import AccountBenefitFilter, AccountFilter, BenefitFilter
from offering.forms import AccountBenefitForm, AccountForm, BenefitForm
from offering.models import Account, AccountBenefit, Benefit
from workshops.base_forms import GenericDeleteForm
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYListView,
    AMYUpdateView,
)
from workshops.filters import EventCategoryFilter
from workshops.forms import EventCategoryForm
from workshops.models import EventCategory
from workshops.utils.access import OnlyForAdminsMixin

REQUIRED_FLAG_NAME = "SERVICE_OFFERING"


# -----------------------------------------------------------------


class AccountList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[Account]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_account"]
    template_name = "offering/account_list.html"
    queryset = Account.objects.order_by("-created_at")
    title = "Accounts"
    filter_class = AccountFilter


class AccountDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[Account]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_account"]
    template_name = "offering/account_details.html"
    model = Account

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class AccountCreate(OnlyForAdminsMixin, FlaggedViewMixin, AMYCreateView[AccountForm, Account]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.add_account"]
    template_name = "offering/account_create.html"
    form_class = AccountForm
    model = Account
    object: Account
    title = "Create a new account"

    def form_valid(self, form: AccountForm) -> HttpResponse:
        obj = form.save(commit=False)
        mapped = Account.ACCOUNT_TYPE_MAPPING[form.cleaned_data["account_type"]]
        obj.generic_relation_content_type = ContentType.objects.get(app_label=mapped[0], model=mapped[1])
        obj.save()
        return super().form_valid(form)


class AccountUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView[AccountForm, Account]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_account", "offering.change_account"]
    template_name = "offering/account_edit.html"
    form_class = AccountForm
    model = Account
    object: Account

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class AccountDelete(OnlyForAdminsMixin, FlaggedViewMixin, AMYDeleteView[Account, GenericDeleteForm[Account]]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.delete_account"]
    model = Account

    def get_success_url(self) -> str:
        return reverse("account-list")


# -----------------------------------------------------------------


class BenefitList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[Benefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_benefit"]
    template_name = "offering/benefit_list.html"
    queryset = Benefit.objects.order_by("-created_at")
    title = "Benefits"
    filter_class = BenefitFilter


class BenefitDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[Benefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_benefit"]
    template_name = "offering/benefit_details.html"
    model = Benefit

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class BenefitCreate(OnlyForAdminsMixin, FlaggedViewMixin, AMYCreateView[BenefitForm, Benefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.add_benefit"]
    template_name = "offering/benefit_create.html"
    form_class = BenefitForm
    model = Benefit
    object: Benefit
    title = "Create a new benefit"


class BenefitUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView[BenefitForm, Benefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_benefit", "offering.change_benefit"]
    template_name = "offering/benefit_edit.html"
    form_class = BenefitForm
    model = Benefit
    object: Benefit

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class BenefitDelete(OnlyForAdminsMixin, FlaggedViewMixin, AMYDeleteView[Benefit, GenericDeleteForm[Benefit]]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.delete_benefit"]
    model = Benefit

    def get_success_url(self) -> str:
        return reverse("benefit-list")


# -----------------------------------------------------------------


class AccountBenefitList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[AccountBenefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_accountbenefit"]
    template_name = "offering/account_benefit_list.html"
    queryset = AccountBenefit.objects.order_by("-created_at")
    title = "Account Benefits"
    filter_class = AccountBenefitFilter


class AccountBenefitDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[AccountBenefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_accountbenefit"]
    template_name = "offering/account_benefit_details.html"
    model = AccountBenefit

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class AccountBenefitCreate(OnlyForAdminsMixin, FlaggedViewMixin, AMYCreateView[AccountBenefitForm, AccountBenefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.add_accountbenefit"]
    template_name = "offering/account_benefit_create.html"
    form_class = AccountBenefitForm
    model = AccountBenefit
    object: AccountBenefit
    title = "Create a new account benefit"


class AccountBenefitUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView[AccountBenefitForm, AccountBenefit]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
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
    OnlyForAdminsMixin, FlaggedViewMixin, AMYDeleteView[AccountBenefit, GenericDeleteForm[AccountBenefit]]
):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.delete_accountbenefit"]
    model = AccountBenefit

    def get_success_url(self) -> str:
        return reverse("account-benefit-list")


# -----------------------------------------------------------------


class EventCategoryList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[EventCategory]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_eventcategory"]
    template_name = "offering/event_category_list.html"
    queryset = EventCategory.objects.order_by("name")
    title = "Event Categories"
    filter_class = EventCategoryFilter


class EventCategoryDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[EventCategory]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.view_eventcategory"]
    template_name = "offering/event_category_details.html"
    model = EventCategory

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f'Event Category "{self.object}"'
        return context


class EventCategoryCreate(OnlyForAdminsMixin, FlaggedViewMixin, AMYCreateView[EventCategoryForm, EventCategory]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.add_eventcategory"]
    template_name = "offering/event_category_create.html"
    form_class = EventCategoryForm
    model = EventCategory
    object: EventCategory
    title = "Create a new event category"


class EventCategoryUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView[EventCategoryForm, EventCategory]):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
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
    OnlyForAdminsMixin, FlaggedViewMixin, AMYDeleteView[EventCategory, GenericDeleteForm[EventCategory]]
):
    flag_name = REQUIRED_FLAG_NAME  # type: ignore
    permission_required = ["offering.delete_eventcategory"]
    model = EventCategory

    def get_success_url(self) -> str:
        return reverse("event-category-list")
