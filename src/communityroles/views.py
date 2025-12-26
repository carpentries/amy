from typing import Any

from django import forms
from django.contrib.auth.mixins import PermissionRequiredMixin

from src.workshops.base_forms import GenericDeleteForm
from src.workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYUpdateView,
    RedirectSupportMixin,
)
from src.workshops.utils.access import OnlyForAdminsMixin

from .forms import CommunityRoleForm, CommunityRoleUpdateForm
from .models import CommunityRole

# ------------------------------------------------------------
# CommunityRole related views


class CommunityRoleDetails(OnlyForAdminsMixin, AMYDetailView[CommunityRole]):
    queryset = CommunityRole.objects.all()
    context_object_name = "role"
    template_name = "communityroles/communityrole.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class CommunityRoleCreate(
    OnlyForAdminsMixin, PermissionRequiredMixin, RedirectSupportMixin, AMYCreateView[CommunityRoleForm, CommunityRole]
):
    permission_required = "communityroles.add_communityrole"
    model = CommunityRole
    form_class = CommunityRoleForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs.update({"prefix": "communityrole"})
        return kwargs


class CommunityRoleUpdate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView[CommunityRoleForm, CommunityRole]):
    permission_required = "communityroles.change_communityrole"
    model = CommunityRole
    form_class = CommunityRoleUpdateForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "prefix": "communityrole",
                "community_role_config": self.object.config,
                "widgets": {"person": forms.HiddenInput()},
            }
        )
        return kwargs


class CommunityRoleDelete(OnlyForAdminsMixin, AMYDeleteView[CommunityRole, GenericDeleteForm[CommunityRole]]):
    permission_required = "communityroles.delete_communityrole"
    model = CommunityRole

    def get_success_url(self) -> str:
        # Currently can only be called via redirect.
        # There is no direct view for all Community Roles.
        return self.request.GET.get("next", "")
