from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.db.models import (
    F,
    Q,
    Count,
    Prefetch,
)
from django.db.models.functions import Now
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView

from fiscal.filters import (
    OrganizationFilter,
    MembershipFilter,
)
from fiscal.forms import (
    OrganizationForm,
    OrganizationCreateForm,
    MembershipForm,
    MembershipCreateForm,
    MemberForm,
    SponsorshipForm,
)
from workshops.base_views import (
    AMYCreateView,
    AMYUpdateView,
    AMYDeleteView,
    AMYListView,
    RedirectSupportMixin,
    AMYDetailView,
)
from workshops.models import (
    Organization,
    Member,
    Membership,
    Sponsorship,
    Task,
    Award,
)
from workshops.util import (
    OnlyForAdminsMixin,
)


# ------------------------------------------------------------
# Organization related views
# ------------------------------------------------------------


class AllOrganizations(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_organizations"
    template_name = "fiscal/all_organizations.html"
    filter_class = OrganizationFilter
    queryset = Organization.objects.prefetch_related(
        Prefetch(
            "membership_set",
            to_attr="current_memberships",
            queryset=Membership.objects.filter(
                agreement_start__lte=Now(),
                agreement_end__gte=Now(),
            ),
        )
    )
    title = "All Organizations"


class OrganizationDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = Organization.objects.all()
    context_object_name = "organization"
    template_name = "fiscal/organization.html"
    slug_field = "domain"
    slug_url_kwarg = "org_domain"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Organization {0}".format(self.object)
        return context


class OrganizationCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView):
    permission_required = "workshops.add_organization"
    model = Organization
    form_class = OrganizationCreateForm

    def get_initial(self):
        initial = {
            "domain": self.request.GET.get("domain", ""),
            "fullname": self.request.GET.get("fullname", ""),
            "comment": self.request.GET.get("comment", ""),
        }
        return initial


class OrganizationUpdate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = "workshops.change_organization"
    model = Organization
    form_class = OrganizationForm
    slug_field = "domain"
    slug_url_kwarg = "org_domain"
    template_name = "generic_form_with_comments.html"


class OrganizationDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Organization
    slug_field = "domain"
    slug_url_kwarg = "org_domain"
    permission_required = "workshops.delete_organization"
    success_url = reverse_lazy("all_organizations")


# ------------------------------------------------------------
# Membership related views
# ------------------------------------------------------------


class AllMemberships(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_memberships"
    template_name = "fiscal/all_memberships.html"
    filter_class = MembershipFilter
    queryset = (
        Membership.objects.annotate(
            instructor_training_seats_total=(
                F("seats_instructor_training")
                + F("additional_instructor_training_seats")
            ),
            # for future reference, in case someone would want to implement
            # this annotation
            # instructor_training_seats_utilized=(
            #     Count('task', filter=Q(task__role__name='learner'))
            # ),
            instructor_training_seats_remaining=(
                F("seats_instructor_training")
                + F("additional_instructor_training_seats")
                - Count("task", filter=Q(task__role__name="learner"))
            ),
        )
        .prefetch_related("organizations")
        .order_by("id")
    )
    title = "All Memberships"


class MembershipDetails(OnlyForAdminsMixin, AMYDetailView):
    prefetch_awards = Prefetch(
        "person__award_set", queryset=Award.objects.select_related("badge")
    )
    queryset = Membership.objects.prefetch_related(
        Prefetch(
            "member_set",
            queryset=Member.objects.select_related(
                "organization", "role", "membership"
            ).order_by("organization__fullname"),
        ),
        Prefetch(
            "task_set",
            queryset=Task.objects.select_related("event", "person").prefetch_related(
                prefetch_awards
            ),
        ),
    )
    context_object_name = "membership"
    template_name = "fiscal/membership.html"
    pk_url_kwarg = "membership_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "{0}".format(self.object)
        return context


class MembershipCreate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    AMYCreateView,
):
    permission_required = [
        "workshops.add_membership",
        "workshops.change_organization",
    ]
    model = Membership
    form_class = MembershipCreateForm

    def form_valid(self, form):
        start: date = form.cleaned_data["agreement_start"]
        next_year = start.replace(year=start.year + 1)
        if next_year != form.cleaned_data["agreement_end"]:
            messages.warning(
                self.request,
                "Membership agreement end is not full year from the start. "
                f"It should be: {next_year:%Y-%m-%d}.",
            )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("membership_members", self.object.pk)


class MembershipUpdate(
    OnlyForAdminsMixin, PermissionRequiredMixin, RedirectSupportMixin, AMYUpdateView
):
    permission_required = "workshops.change_membership"
    model = Membership
    form_class = MembershipForm
    pk_url_kwarg = "membership_id"
    template_name = "generic_form_with_comments.html"


class MembershipDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Membership
    permission_required = "workshops.delete_membership"
    pk_url_kwarg = "membership_id"

    def get_success_url(self):
        return reverse("all_memberships")


class MembershipMembers(OnlyForAdminsMixin, FormView):
    template_name = "fiscal/membership_members.html"
    form_class = modelformset_factory(Member, MemberForm, extra=0, can_delete=True)

    def dispatch(self, request, *args, **kwargs):
        self.membership = get_object_or_404(Membership, pk=self.kwargs["membership_id"])
        return super().dispatch(request, *args, **kwargs)

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["queryset"] = self.membership.member_set.select_related(
            "organization", "role", "membership"
        ).order_by("organization__fullname")
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs["membership"] = self.membership
        kwargs["formset"] = self.get_form()
        if "title" not in kwargs:
            kwargs["title"] = "Change members for {}".format(self.membership)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return self.membership.get_absolute_url()


# ------------------------------------------------------------
# Sponsorship related views
# ------------------------------------------------------------


class SponsorshipCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView):
    model = Sponsorship
    permission_required = "workshops.add_sponsorship"
    form_class = SponsorshipForm

    def get_success_url(self):
        return reverse("event_edit", args=[self.object.event.slug]) + "#sponsors"


class SponsorshipDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Sponsorship
    permission_required = "workshops.delete_sponsorship"

    def get_success_url(self):
        return reverse("event_edit", args=[self.get_object().event.slug]) + "#sponsors"
