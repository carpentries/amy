from datetime import date, timedelta

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
    MembershipRollOverForm,
    MemberForm,
    MembershipTaskForm,
    MembershipExtensionForm,
)
from fiscal.models import MembershipTask
from fiscal.base_views import (
    GetMembershipMixin,
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
    queryset = Organization.objects.prefetch_related("memberships")
    context_object_name = "organization"
    template_name = "fiscal/organization.html"
    slug_field = "domain"
    slug_url_kwarg = "org_domain"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Organization {0}".format(self.object)
        context["all_events"] = (
            self.object.hosted_events.all()
            .union(
                self.object.sponsored_events.all(),
                self.object.administered_events.all(),
            )
            .prefetch_related("tags")
        )
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
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # TODO: improve
            ),
            # for future reference, in case someone would want to implement
            # this annotation
            # instructor_training_seats_utilized=(
            #     Count('task', filter=Q(task__role__name='learner'))
            # ),
            instructor_training_seats_remaining=(
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # TODO: improve
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


class MembershipMembers(
    OnlyForAdminsMixin, PermissionRequiredMixin, MembershipFormsetView
):
    permission_required = "workshops.change_membership"

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


class MembershipTasks(
    OnlyForAdminsMixin, PermissionRequiredMixin, MembershipFormsetView
):
    permission_required = "workshops.change_membership"

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


class MembershipExtend(
    OnlyForAdminsMixin, PermissionRequiredMixin, GetMembershipMixin, FormView
):
    form_class = MembershipExtensionForm
    template_name = "generic_form.html"
    permission_required = "workshops.change_membership"

    def get_initial(self):
        return {
            "agreement_start": self.membership.agreement_start,
            "agreement_end": self.membership.agreement_end,
            "extension": 0,
            "new_agreement_end": self.membership.agreement_end,
        }

    def get_context_data(self, **kwargs):
        if "title" not in kwargs:
            kwargs["title"] = f"Extend membership {self.membership}"
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        days = form.cleaned_data["extension"]
        extension = timedelta(days=days)
        self.membership.agreement_end += extension
        self.membership.extended = days
        self.membership.save()

        return super().form_valid(form)

    def get_success_url(self) -> str:
        return self.membership.get_absolute_url()


class MembershipCreateRollOver(
    OnlyForAdminsMixin, PermissionRequiredMixin, GetMembershipMixin, AMYCreateView
):
    permission_required = ["workshops.create_membership", "workshops.change_membership"]
    template_name = "generic_form.html"
    model = Membership
    form_class = MembershipRollOverForm
    pk_url_kwarg = "membership_id"

    def get_initial(self):
        return {
            "name": self.membership.name,
            "consortium": self.membership.consortium,
            "public_status": self.membership.public_status,
            "variant": self.membership.variant,
            "agreement_start": self.membership.agreement_end,
            "agreement_end": date(
                self.membership.agreement_end.year + 1,
                self.membership.agreement_end.month,
                self.membership.agreement_end.day,
            ),
            "contribution_type": self.membership.contribution_type,
            "registration_code": self.membership.registration_code,
            "agreement_link": self.membership.agreement_link,
            "workshops_without_admin_fee_per_agreement": self.membership.workshops_without_admin_fee_per_agreement,  # noqa
            "workshops_without_admin_fee_rolled_from_previous": self.membership.workshops_without_admin_fee_remaining,  # noqa
            "public_instructor_training_seats": self.membership.public_instructor_training_seats,  # noqa
            "additional_public_instructor_training_seats": self.membership.additional_public_instructor_training_seats,  # noqa
            "public_instructor_training_seats_rolled_from_previous": self.membership.seats_instructor_training_remaining,  # noqa
            "inhouse_instructor_training_seats": self.membership.inhouse_instructor_training_seats,  # noqa
            "additional_inhouse_instructor_training_seats": self.membership.additional_inhouse_instructor_training_seats,  # noqa
            "inhouse_instructor_training_seats_rolled_from_previous": self.membership.seats_instructor_training_remaining,  # noqa  # TODO
            "emergency_contact": self.membership.emergency_contact,
        }

    def get_context_data(self, **kwargs):
        kwargs["title"] = f"Create new membership from {self.membership}"
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        # set rolled_from_previous fields to the same values as in initial form data
        form.instance.workshops_without_admin_fee_rolled_from_previous = (
            self.membership.workshops_without_admin_fee_remaining
        )
        form.instance.public_instructor_training_seats_rolled_from_previous = (
            self.membership.seats_instructor_training_remaining
        )
        form.instance.inhouse_instructor_training_seats_rolled_from_previous = (
            self.membership.seats_instructor_training_remaining  # TODO
        )

        # save values rolled over in membership
        self.membership.workshops_without_admin_fee_rolled_over = (
            form.instance.workshops_without_admin_fee_rolled_from_previous
        )
        self.membership.public_instructor_training_seats_rolled_over = (
            form.instance.public_instructor_training_seats_rolled_from_previous
        )
        self.membership.inhouse_instructor_training_seats_rolled_over = (
            form.instance.inhouse_instructor_training_seats_rolled_from_previous
        )
        self.membership.save()

        # create the object and store returned success url redirect
        result = super().form_valid(form)

        # duplicate members and membership tasks from old membership to the new one
        Member.objects.bulk_create(
            [
                Member(membership=self.object, organization=m.organization, role=m.role)
                for m in self.membership.member_set.all()
            ]
        )
        MembershipTask.objects.bulk_create(
            [
                MembershipTask(membership=self.object, person=m.person, role=m.role)
                for m in self.membership.membershiptask_set.all()
            ]
        )

        return result

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()
