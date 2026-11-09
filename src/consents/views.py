from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import BaseForm, HiddenInput
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import Http404, HttpResponseBase
from django.shortcuts import get_object_or_404
from rest_framework.reverse import reverse

from src.consents.forms import ActiveTermConsentsForm, RequiredConsentsForm
from src.consents.models import Consent
from src.consents.util import person_has_consented_to_required_terms
from src.workshops.base_views import AMYCreateView, AMYFormView
from src.workshops.models import Person
from src.workshops.utils.urls import safe_next_or_default_url


class ConsentsUpdate(LoginRequiredMixin, UserPassesTestMixin, AMYCreateView[ActiveTermConsentsForm, Consent]):
    """Save consents for the person from the URL. The form is rendered on the person edit page
    (PersonUpdate) and only POSTs here, so this view has no template of its own."""

    model = Consent
    form_class = ActiveTermConsentsForm
    http_method_names = ["post"]

    def test_func(self) -> bool:
        # Same access rule as PersonUpdate, which renders this form.
        user = self.request.user
        return user.has_perm("workshops.change_person") or user.pk == self.kwargs["person_id"]

    def get_person(self) -> Person:
        if not hasattr(self, "person"):
            self.person = get_object_or_404(Person, pk=self.kwargs["person_id"])
        return self.person

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        person = self.get_person()
        # Always save consents for the person from the URL (on which the permission check was
        # done), ignoring any person ID submitted in the form.
        data = kwargs["data"].copy()
        data["consents-person"] = str(person.pk)
        kwargs.update({"data": data, "prefix": "consents", "initial": {"person": person}})
        return kwargs

    def get_success_url(self) -> str:
        default_url = reverse("person_edit", kwargs={"person_id": self.get_person().pk})
        return safe_next_or_default_url(self.request.GET.get("next"), default=default_url)

    def get_success_message(self, *args: Any, **kwargs: Any) -> str:
        return "Consents were successfully updated."

    def form_invalid(self, form: BaseForm) -> HttpResponse:
        # No template to re-render the form with; report errors and go back.
        errors = "; ".join(f"{field}: {', '.join(str(e) for e in errs)}" for field, errs in form.errors.items())
        messages.error(self.request, f"Consents were not updated. {errors}")
        return HttpResponseRedirect(self.get_success_url())


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
