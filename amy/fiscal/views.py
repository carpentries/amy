from datetime import date, timedelta
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Prefetch, QuerySet
from django.db.models.functions import Now
from django.forms import BaseModelFormSet, modelformset_factory
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView

from communityroles.models import CommunityRole
from emails.actions.exceptions import EmailStrategyException
from emails.actions.membership_quarterly_emails import (
    membership_quarterly_email_strategy,
    run_membership_quarterly_email_strategy,
)
from emails.actions.new_membership_onboarding import (
    new_membership_onboarding_strategy,
    run_new_membership_onboarding_strategy,
)
from emails.signals import (
    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
)
from emails.types import StrategyEnum
from extcomments.utils import add_comment_for_object
from fiscal.base_views import (
    GetMembershipMixin,
    MembershipFormsetView,
    UnquoteSlugMixin,
)
from fiscal.filters import MembershipFilter, OrganizationFilter
from fiscal.forms import (
    MemberForm,
    MembershipCreateForm,
    MembershipExtensionForm,
    MembershipForm,
    MembershipRollOverForm,
    MembershipTaskForm,
    OrganizationCreateForm,
    OrganizationForm,
)
from fiscal.models import MembershipTask
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYListView,
    AMYUpdateView,
    AuthenticatedHttpRequest,
    RedirectSupportMixin,
)
from workshops.models import Award, Member, MemberRole, Membership, Organization, Task
from workshops.utils.access import OnlyForAdminsMixin

# ------------------------------------------------------------
# Organization related views
# ------------------------------------------------------------


class AllOrganizations(OnlyForAdminsMixin, AMYListView[Organization]):
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


class OrganizationDetails(UnquoteSlugMixin, OnlyForAdminsMixin, AMYDetailView):
    queryset = Organization.objects.prefetch_related("memberships")
    context_object_name = "organization"
    template_name = "fiscal/organization.html"
    slug_field = "domain"
    slug_url_kwarg = "org_domain"
    object: Organization

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = "Organization {0}".format(self.object)
        related = ["host", "sponsor", "membership"]
        context["all_events"] = (
            self.object.hosted_events.select_related(*related)
            .prefetch_related("tags")
            .union(
                self.object.sponsored_events.select_related(*related),
                self.object.administered_events.select_related(*related),
            )
        )
        context["main_organisation_memberships"] = Membership.objects.filter(
            member__role__name="main", member__organization=self.object
        )
        return context


class OrganizationCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView):
    permission_required = "workshops.add_organization"
    model = Organization
    form_class = OrganizationCreateForm

    def get_initial(self) -> dict[str, str]:
        initial = {
            "domain": self.request.GET.get("domain", ""),
            "fullname": self.request.GET.get("fullname", ""),
            "comment": self.request.GET.get("comment", ""),
        }
        return initial


class OrganizationUpdate(UnquoteSlugMixin, OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = "workshops.change_organization"
    model = Organization
    form_class = OrganizationForm
    slug_field = "domain"
    slug_url_kwarg = "org_domain"
    template_name = "generic_form_with_comments.html"


class OrganizationDelete(UnquoteSlugMixin, OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Organization
    slug_field = "domain"
    slug_url_kwarg = "org_domain"
    permission_required = "workshops.delete_organization"
    success_url = reverse_lazy("all_organizations")


# ------------------------------------------------------------
# Membership related views
# ------------------------------------------------------------


class AllMemberships(OnlyForAdminsMixin, AMYListView[Membership]):
    context_object_name = "all_memberships"
    template_name = "fiscal/all_memberships.html"
    filter_class = MembershipFilter
    queryset = Membership.objects.annotate_with_seat_usage().prefetch_related("organizations").order_by("id")
    title = "All Memberships"


class MembershipDetails(OnlyForAdminsMixin, AMYDetailView):
    prefetch_awards = Prefetch("person__award_set", queryset=Award.objects.select_related("badge"))
    queryset = Membership.objects.prefetch_related(
        Prefetch(
            "member_set",
            queryset=Member.objects.select_related("organization", "role", "membership").order_by(
                "organization__fullname"
            ),
        ),
        Prefetch(
            "membershiptask_set",
            queryset=MembershipTask.objects.select_related("person", "role", "membership").order_by(
                "person__family", "person__personal", "role__name"
            ),
        ),
        Prefetch(
            "task_set",
            queryset=Task.objects.select_related("event", "person").prefetch_related(prefetch_awards),
        ),
    )
    context_object_name = "membership"
    template_name = "fiscal/membership.html"
    pk_url_kwarg = "membership_id"
    object: Membership

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = "{0}".format(self.object)
        context["membership_extensions_sum"] = sum(self.object.extensions)
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
    object: Membership
    form_class = MembershipCreateForm

    def form_valid(self, form: MembershipCreateForm) -> HttpResponse:
        start: date = form.cleaned_data["agreement_start"]
        next_year = start.replace(year=start.year + 1)
        if next_year != form.cleaned_data["agreement_end"]:
            messages.warning(
                self.request,
                f"Membership agreement end is not full year from the start. It should be: {next_year:%Y-%m-%d}.",
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

    def get_success_url(self) -> str:
        path = "membership_members" if self.consortium else "membership_details"
        return reverse(path, args=[self.object.pk])


class MembershipUpdate(OnlyForAdminsMixin, PermissionRequiredMixin, RedirectSupportMixin, AMYUpdateView):
    permission_required = "workshops.change_membership"
    model = Membership
    object: Membership
    form_class = MembershipForm
    pk_url_kwarg = "membership_id"
    template_name = "generic_form_with_comments.html"
    request: AuthenticatedHttpRequest

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()

        show_rolled_over = False
        show_rolled_from_previous = False
        if self.object.rolled_to_membership:
            show_rolled_over = True

        try:
            if self.object.rolled_from_membership:
                show_rolled_from_previous = True
        except Membership.DoesNotExist:
            pass

        kwargs["show_rolled_over"] = show_rolled_over
        kwargs["show_rolled_from_previous"] = show_rolled_from_previous
        return kwargs

    def form_valid(self, form: MembershipForm) -> HttpResponse:
        result = super().form_valid(form)
        data = form.cleaned_data

        if form.initial["extensions"] != data["extensions"]:
            # Since the extensions have changed, the end date needs to be recalculated.
            changed_days = sum(data["extensions"]) - sum(form.initial["extensions"])
            self.object.agreement_end += timedelta(days=changed_days)
            self.object.save()

            # User changed extensions values, let's add a comment indicating the change.
            str_ext = ", ".join(str(extension) for extension in data["extensions"])
            comment = (
                f"Extension days changed to following: {str_ext} days. New agreement "
                f"end date: {self.object.agreement_end}."
            )
            add_comment_for_object(self.object, self.request.user, comment)

        # see if updated "rolled" values are available, and update related memberships
        pairs = (
            (
                "workshops_without_admin_fee_rolled_over",
                "workshops_without_admin_fee_rolled_from_previous",
            ),
            (
                "public_instructor_training_seats_rolled_over",
                "public_instructor_training_seats_rolled_from_previous",
            ),
            (
                "inhouse_instructor_training_seats_rolled_over",
                "inhouse_instructor_training_seats_rolled_from_previous",
            ),
        )
        save_rolled_to = False
        try:
            for rolled_over, rolled_from in pairs:
                if rolled_over in data:
                    setattr(
                        self.object.rolled_to_membership,
                        rolled_from,
                        data[rolled_over],
                    )
                    save_rolled_to = True

            if save_rolled_to:
                self.object.rolled_to_membership.save()  # type: ignore
        except Membership.DoesNotExist:
            pass

        save_rolled_from = False
        try:
            for rolled_over, rolled_from in pairs:
                if rolled_from in data:
                    setattr(
                        self.object.rolled_from_membership,
                        rolled_over,
                        data[rolled_from],
                    )
                    save_rolled_from = True

            if save_rolled_from:
                self.object.rolled_from_membership.save()
        except Membership.DoesNotExist:
            pass

        try:
            run_new_membership_onboarding_strategy(
                new_membership_onboarding_strategy(self.object),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                    self.object,
                ),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                    self.object,
                ),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                    self.object,
                ),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        return result


class MembershipDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Membership
    object: Membership
    permission_required = "workshops.delete_membership"
    pk_url_kwarg = "membership_id"

    def before_delete(self, *args: Any, **kwargs: Any) -> None:
        """Save for use in `after_delete` method."""
        membership = self.object

        # Check for any remaining objects referencing this membership.
        # Since membership tasks are expected for the scheduled email, then they have
        # to be removed first, which would de-schedule the email.
        if not (
            Member.objects.filter(membership=membership).count()
            or MembershipTask.objects.filter(membership=membership).count()
            or Task.objects.filter(seat_membership=membership).count()
            or CommunityRole.objects.filter(membership=membership).count()
        ):
            try:
                run_new_membership_onboarding_strategy(
                    StrategyEnum.CANCEL,  # choosing the strategy manually
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when running new membership - onboarding strategy. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                    StrategyEnum.CANCEL,  # choosing the strategy manually
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when running membership quarterly 3 months strategy. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                    StrategyEnum.CANCEL,  # choosing the strategy manually
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when running membership quarterly 6 months strategy. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                    StrategyEnum.CANCEL,  # choosing the strategy manually
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when running membership quarterly 9 months strategy. {exc}",
                )
        else:
            messages.warning(
                self.request,
                "Not attempting to remove related scheduled emails, because there are "
                "still related objects in the database.",
            )

    def get_success_url(self) -> str:
        return reverse("all_memberships")


class MembershipMembers(OnlyForAdminsMixin, PermissionRequiredMixin, MembershipFormsetView[Member, MemberForm]):
    permission_required = (
        "workshops.change_membership",
        "workshops.add_member",
        "workshops.change_member",
        "workshops.delete_member",
    )
    request: AuthenticatedHttpRequest

    def get_formset(self, *args: Any, **kwargs: Any) -> type[BaseModelFormSet[Member, MemberForm]]:
        return modelformset_factory(Member, MemberForm, *args, **kwargs)

    def get_formset_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        if not self.membership.consortium:
            kwargs["can_delete"] = False
            kwargs["max_num"] = 1
            kwargs["validate_max"] = True
        return kwargs

    def get_formset_queryset(self, object: Membership) -> QuerySet[Member]:
        return object.member_set.select_related("organization", "role", "membership").order_by("organization__fullname")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if "title" not in kwargs:
            kwargs["title"] = "Change members for {}".format(self.membership)
        if not self.membership.consortium:
            kwargs["add_another_help_text"] = (
                "Only one affiliated organisation can be listed because this is not "
                "a consortium membership. If you would like to list more than one "
                "affiliated organisation, please select 'Consortium' in the "
                "membership view."
            )
        return super().get_context_data(**kwargs)

    def form_valid(self, formset: BaseModelFormSet[Member, MemberForm]) -> HttpResponse:
        result = super().form_valid(formset)

        # Figure out changes in members and add comment listing them.
        comment = "Changed members on {date}:\n\n{comments}"
        added = "* Added {organization}"
        removed = "* Removed {organization}"
        changed = "* Replaced with {organization}"

        comments = (
            [added.format(organization=member.organization) for member in formset.new_objects]
            + [removed.format(organization=member.organization) for member in formset.deleted_objects]
            + [
                # it's difficult to figure out previous value of member.organization,
                # so the comment will only contain the new version
                changed.format(organization=member.organization)
                for member, fields in formset.changed_objects
                if "organization" in fields
            ]
        )

        if comments:
            add_comment_for_object(
                self.membership,
                self.request.user,
                comment.format(date=date.today(), comments="\n".join(comments)),
            )

        return result


class MembershipTasks(
    OnlyForAdminsMixin, PermissionRequiredMixin, MembershipFormsetView[MembershipTask, MembershipTaskForm]
):
    permission_required = "workshops.change_membership"

    def get_formset(self, *args: Any, **kwargs: Any) -> type[BaseModelFormSet[MembershipTask, MembershipTaskForm]]:
        return modelformset_factory(MembershipTask, MembershipTaskForm, *args, **kwargs)

    def get_formset_queryset(self, object: Membership) -> QuerySet[MembershipTask]:
        return object.membershiptask_set.select_related("person", "role", "membership").order_by(
            "person__family", "person__personal", "role__name"
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if "title" not in kwargs:
            kwargs["title"] = "Change person roles for {}".format(self.membership)
        return super().get_context_data(**kwargs)

    def form_valid(self, formset: BaseModelFormSet[MembershipTask, MembershipTaskForm]) -> HttpResponse:
        result = super().form_valid(formset)

        try:
            run_new_membership_onboarding_strategy(
                new_membership_onboarding_strategy(self.membership),
                request=self.request,
                membership=self.membership,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                    self.membership,
                ),
                request=self.request,
                membership=self.membership,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                    self.membership,
                ),
                request=self.request,
                membership=self.membership,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                    self.membership,
                ),
                request=self.request,
                membership=self.membership,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        return result


class MembershipExtend(
    OnlyForAdminsMixin, PermissionRequiredMixin, GetMembershipMixin, FormView[MembershipExtensionForm]
):
    form_class = MembershipExtensionForm
    template_name = "generic_form.html"
    permission_required = "workshops.change_membership"
    comment = "Extended membership by {days} days on {date} (new end date: {new_date}).\n\n----\n\n{comment}"
    request: AuthenticatedHttpRequest

    def get_initial(self) -> dict[str, Any]:
        return {
            "agreement_start": self.membership.agreement_start,
            "agreement_end": self.membership.agreement_end,
            "extension": 0,
            "new_agreement_end": self.membership.agreement_end,
        }

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if "title" not in kwargs:
            kwargs["title"] = f"Extend membership {self.membership}"
        return super().get_context_data(**kwargs)

    def form_valid(self, form: MembershipExtensionForm) -> HttpResponse:
        agreement_end = form.cleaned_data["agreement_end"]
        new_agreement_end = form.cleaned_data["new_agreement_end"]
        days = (new_agreement_end - agreement_end).days
        comment = form.cleaned_data["comment"]
        self.membership.agreement_end = new_agreement_end
        self.membership.extensions.append(days)
        self.membership.save()

        # Add a comment "Extended membership by X days on DATE" on user's behalf.
        add_comment_for_object(
            self.membership,
            self.request.user,
            self.comment.format(
                days=days,
                date=date.today(),
                new_date=new_agreement_end,
                comment=comment,
            ),
        )

        return super().form_valid(form)

    def get_success_url(self) -> str:
        return self.membership.get_absolute_url()


class MembershipCreateRollOver(OnlyForAdminsMixin, PermissionRequiredMixin, GetMembershipMixin, AMYCreateView):
    permission_required = ["workshops.create_membership", "workshops.change_membership"]
    template_name = "generic_form.html"
    model = Membership
    object: Membership
    form_class = MembershipRollOverForm
    pk_url_kwarg = "membership_id"
    success_message = 'Membership "{membership}" was successfully rolled-over to a new ' 'membership "{new_membership}"'

    def membership_queryset_kwargs(self) -> dict[str, Any]:
        # Prevents already rolled-over memberships from rolling-over again.
        return dict(rolled_to_membership__isnull=True)

    def get_success_message(self, cleaned_data: dict[str, Any]) -> str:
        return self.success_message.format(
            cleaned_data,
            membership=str(self.membership),
            new_membership=str(self.object),
        )

    def get_initial(self) -> Dict[str, Any]:
        return {
            "name": self.membership.name,
            "consortium": self.membership.consortium,
            "public_status": self.membership.public_status,
            "variant": self.membership.variant,
            "agreement_start": self.membership.agreement_end + timedelta(days=1),
            "agreement_end": date(
                self.membership.agreement_end.year + 1,
                self.membership.agreement_end.month,
                self.membership.agreement_end.day,
            ),
            "contribution_type": self.membership.contribution_type,
            "registration_code": self.membership.registration_code,
            "workshops_without_admin_fee_per_agreement": self.membership.workshops_without_admin_fee_per_agreement,  # noqa
            "workshops_without_admin_fee_rolled_from_previous": 0,
            "public_instructor_training_seats": self.membership.public_instructor_training_seats,  # noqa
            "additional_public_instructor_training_seats": self.membership.additional_public_instructor_training_seats,  # noqa
            "public_instructor_training_seats_rolled_from_previous": 0,
            "inhouse_instructor_training_seats": self.membership.inhouse_instructor_training_seats,  # noqa
            "additional_inhouse_instructor_training_seats": self.membership.additional_inhouse_instructor_training_seats,  # noqa
            "inhouse_instructor_training_seats_rolled_from_previous": 0,
            "emergency_contact": self.membership.emergency_contact,
        }

    def get_form_kwargs(self) -> Dict[str, Any]:
        # if any of the values is negative, use 0
        max_values = {
            "workshops_without_admin_fee_rolled_from_previous": max(
                self.membership.workshops_without_admin_fee_remaining, 0
            ),
            "public_instructor_training_seats_rolled_from_previous": max(
                self.membership.public_instructor_training_seats_remaining, 0
            ),
            "inhouse_instructor_training_seats_rolled_from_previous": max(
                self.membership.inhouse_instructor_training_seats_remaining, 0
            ),
        }
        return {
            "max_values": max_values,
            **super().get_form_kwargs(),
        }

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        kwargs["title"] = f"Create new membership from {self.membership}"
        return super().get_context_data(**kwargs)

    def form_valid(self, form: MembershipRollOverForm) -> HttpResponse:
        # create new membership, available in self.object
        result = super().form_valid(form)

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
        self.membership.rolled_to_membership = self.object
        self.membership.save()

        # duplicate members and membership tasks from old membership to the new one
        if form.cleaned_data["copy_members"]:
            Member.objects.bulk_create(
                [
                    Member(membership=self.object, organization=m.organization, role=m.role)
                    for m in self.membership.member_set.all()
                ]
            )

        if form.cleaned_data["copy_membership_tasks"]:
            MembershipTask.objects.bulk_create(
                [
                    MembershipTask(membership=self.object, person=m.person, role=m.role)
                    for m in self.membership.membershiptask_set.all()
                ]
            )

        try:
            run_new_membership_onboarding_strategy(
                new_membership_onboarding_strategy(self.object),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                    self.object,
                ),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                    self.object,
                ),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        try:
            run_membership_quarterly_email_strategy(
                MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                    self.object,
                ),
                request=self.request,
                membership=self.object,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )

        return result

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()
