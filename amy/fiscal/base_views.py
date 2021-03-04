from django.shortcuts import get_object_or_404
from django.views.generic import FormView

from workshops.models import Membership


class GetMembershipMixin:
    def dispatch(self, request, *args, **kwargs):
        self.membership = get_object_or_404(Membership, pk=self.kwargs["membership_id"])
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
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs["formset"] = self.get_form()
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        instances = form.save(commit=False)

        # assign membership to any new/changed instance
        for instance in instances:
            instance.membership = self.membership
            instance.save()

        # remove deleted objects
        for instance in form.deleted_objects:
            instance.delete()

        return super().form_valid(form)

    def get_success_url(self):
        return self.membership.get_absolute_url()
