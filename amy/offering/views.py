from typing import Any

from django.urls import reverse
from flags.views import FlaggedViewMixin

from offering.filters import AccountFilter, EventCategoryFilter
from offering.forms import AccountForm, EventCategoryForm
from offering.models import Account, EventCategory
from workshops.base_forms import GenericDeleteForm
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYListView,
    AMYUpdateView,
)
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
