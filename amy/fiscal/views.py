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
from django.urls import reverse, reverse_lazy

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
    MembershipTaskForm,
    SponsorshipForm,
)
from fiscal.models import MembershipTask
from fiscal.base_views import (
    MembershipFormsetView,
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
    MemberRole,
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
            "memberships",
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
            "membershiptask_set",
            queryset=MembershipTask.objects.select_related(
                "person", "role", "membership"
            ).order_by("person__family", "person__personal", "role__name"),
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

        main_organization: Organization = form.cleaned_data["main_organization"]
        self.consortium: bool = form.cleaned_data["consortium"]

        return_data = super().form_valid(form)

        if self.consortium:
            self.object.member_set.create(
                organization=main_organization,
                role=MemberRole.objects.get(name="contract_signatory"),
                membership=self.object,
            )
        else:
            self.object.member_set.create(
                organization=main_organization,
                role=MemberRole.objects.get(name="main"),
                membership=self.object,
            )

        return return_data

    def get_success_url(self):
        path = "membership_members" if self.consortium else "membership_details"
        return reverse(path, args=[self.object.pk])


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


class MembershipMembers(OnlyForAdminsMixin, MembershipFormsetView):
    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        if not self.membership.consortium:
            kwargs["can_delete"] = False
            kwargs["max_num"] = 1
            kwargs["validate_max"] = True
        return kwargs

    def get_formset(self, *args, **kwargs):
        return modelformset_factory(Member, MemberForm, *args, **kwargs)

    def get_formset_queryset(self, object):
        return object.member_set.select_related(
            "organization", "role", "membership"
        ).order_by("organization__fullname")

    def get_context_data(self, **kwargs):
        if "title" not in kwargs:
            kwargs["title"] = "Change members for {}".format(self.membership)
        return super().get_context_data(**kwargs)


class MembershipTasks(OnlyForAdminsMixin, MembershipFormsetView):
    def get_formset(self, *args, **kwargs):
        return modelformset_factory(MembershipTask, MembershipTaskForm, *args, **kwargs)

    def get_formset_queryset(self, object):
        return object.membershiptask_set.select_related(
            "person", "role", "membership"
        ).order_by("person__family", "person__personal", "role__name")

    def get_context_data(self, **kwargs):
        if "title" not in kwargs:
            kwargs["title"] = "Change person roles for {}".format(self.membership)
        return super().get_context_data(**kwargs)


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
