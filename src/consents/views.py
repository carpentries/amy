from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import HiddenInput
from django.http import HttpRequest, HttpResponse
from django.http.response import Http404, HttpResponseBase
from rest_framework.reverse import reverse

from src.consents.forms import ActiveTermConsentsForm, RequiredConsentsForm
from src.consents.models import Consent
from src.consents.util import person_has_consented_to_required_terms
from src.workshops.base_views import (
    AMYCreateView,
    AMYFormView,
    RedirectSupportMixin,
)
from src.workshops.utils.urls import safe_next_or_default_url


class ConsentsUpdate(RedirectSupportMixin, AMYCreateView[ActiveTermConsentsForm, Consent], LoginRequiredMixin):
    model = Consent
    form_class = ActiveTermConsentsForm

    def get_success_url(self) -> str:
        # Currently can only be called via redirect.
        # There is no direct view for Consents.
        next_url = self.request.GET["next"]
        return next_url

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        person = kwargs["data"]["consents-person"]
        kwargs.update({"prefix": "consents", "initial": {"person": person}})
        return kwargs

    def get_success_message(self, *args: Any, **kwargs: Any) -> str:
        return "Consents were successfully updated."


class ActionRequiredTerms(LoginRequiredMixin, AMYFormView[RequiredConsentsForm]):
    form_class = RequiredConsentsForm
    template_name = "consents/action_required_terms.html"
    title = "Action required: terms agreement"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        # Disable the view for users who already agreed. Anonymous users are
        # redirected to login by LoginRequiredMixin's dispatch (via super()).
        if request.user.is_authenticated and person_has_consented_to_required_terms(request.user):
            raise Http404("This view is disabled.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {"person": self.request.user}
        kwargs["widgets"] = {"person": HiddenInput()}
        return kwargs

    def form_valid(self, form: RequiredConsentsForm) -> HttpResponse:
        form.save()
        messages.success(self.request, "Agreement successfully saved.")
        return super().form_valid(form)

    def form_invalid(self, form: RequiredConsentsForm) -> HttpResponse:
        messages.error(self.request, "Fix errors below.")
        return super().form_invalid(form)

    def get_success_url(self) -> str:
        return safe_next_or_default_url(self.request.GET.get("next"), default=reverse("dispatch"))
