from typing import Any, TypeVar
from urllib.parse import unquote

from django.db.models import Model
from django.forms import BaseModelFormSet, ModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404
from django.views.generic import FormView

from workshops.models import Membership

_M = TypeVar("_M", bound=Model)
_ModelFormT = TypeVar("_ModelFormT", bound=ModelForm[_M])  # type: ignore


class GetMembershipMixin:
    def membership_queryset_kwargs(self) -> dict[str, str]:
        return {}

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.membership = get_object_or_404(
            Membership,
            pk=self.kwargs["membership_id"],  # type: ignore
            **self.membership_queryset_kwargs(),
        )
        return super().dispatch(request, *args, **kwargs)  # type: ignore

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        kwargs["membership"] = self.membership
        return super().get_context_data(**kwargs)  # type: ignore


class MembershipFormsetView(GetMembershipMixin, FormView[BaseModelFormSet[_M, _ModelFormT]]):  # type: ignore
    template_name = "fiscal/membership_formset.html"

    def get_formset_kwargs(self) -> dict[str, Any]:
        return {
            "extra": 0,
            "can_delete": True,
        }

    def get_form_class(self) -> type[BaseModelFormSet[_M, _ModelFormT]]:
        return self.get_formset(**self.get_formset_kwargs())  # type: ignore

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["queryset"] = self.get_formset_queryset(self.membership)  # type: ignore
        kwargs["form_kwargs"] = dict(initial={"membership": self.membership})
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        kwargs["formset"] = self.get_form()
        return super().get_context_data(**kwargs)

    def form_valid(self, formset: BaseModelFormSet[_M, _ModelFormT]) -> HttpResponse:
        formset.save()  # handles adding, updating and deleting instances
        return super().form_valid(formset)

    def get_success_url(self) -> str:
        return self.membership.get_absolute_url()


class UnquoteSlugMixin:
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)  # type: ignore
        slug_url = self.kwargs.get(self.slug_url_kwarg)  # type: ignore
        if slug_url is not None:
            self.kwargs[self.slug_url_kwarg] = unquote(slug_url)  # type: ignore
