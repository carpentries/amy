from urllib.parse import unquote

from django.shortcuts import get_object_or_404
from django.views.generic import FormView

from workshops.models import Membership


class GetMembershipMixin:
    def membership_queryset_kwargs(self):
        return {}

    def dispatch(self, request, *args, **kwargs):
        self.membership = get_object_or_404(
            Membership,
            pk=self.kwargs["membership_id"],
            **self.membership_queryset_kwargs(),
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs["membership"] = self.membership
        return super().get_context_data(**kwargs)


class MembershipFormsetView(GetMembershipMixin, FormView):
    template_name = "fiscal/membership_formset.html"

    def get_formset_kwargs(self):
        return {
            "extra": 0,
            "can_delete": True,
        }

    def get_form_class(self):
        return self.get_formset(**self.get_formset_kwargs())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["queryset"] = self.get_formset_queryset(self.membership)
        kwargs["form_kwargs"] = dict(initial={"membership": self.membership})
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs["formset"] = self.get_form()
        return super().get_context_data(**kwargs)

    def form_valid(self, formset):
        formset.save()  # handles adding, updating and deleting instances
        return super().form_valid(formset)

    def get_success_url(self):
        return self.membership.get_absolute_url()


class UnquoteSlugMixin:
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        slug_url = self.kwargs.get(self.slug_url_kwarg)
        if slug_url is not None:
            self.kwargs[self.slug_url_kwarg] = unquote(slug_url)
