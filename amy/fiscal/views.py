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
    SponsorshipForm,
)
from workshops.base_views import (
    AMYCreateView,
    AMYUpdateView,
    AMYDeleteView,
    AMYListView,
    RedirectSupportMixin,
    PrepopulationSupportMixin,
    AMYDetailView,
)
from workshops.models import (
    Organization,
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
    context_object_name = 'all_organizations'
    template_name = 'fiscal/all_organizations.html'
    filter_class = OrganizationFilter
    queryset = Organization.objects.prefetch_related(Prefetch(
        'membership_set',
        to_attr='current_memberships',
        queryset=Membership.objects.filter(
            agreement_start__lte=Now(),
            agreement_end__gte=Now(),
        )
    ))
    title = 'All Organizations'


class OrganizationDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = Organization.objects.all()
    context_object_name = 'organization'
    template_name = 'fiscal/organization.html'
    slug_field = 'domain'
    slug_url_kwarg = 'org_domain'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Organization {0}'.format(self.object)
        return context


class OrganizationCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                         AMYCreateView):
    permission_required = 'workshops.add_organization'
    model = Organization
    form_class = OrganizationCreateForm


class OrganizationUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                         AMYUpdateView):
    permission_required = 'workshops.change_organization'
    model = Organization
    form_class = OrganizationForm
    slug_field = 'domain'
    slug_url_kwarg = 'org_domain'
    template_name = 'generic_form_with_comments.html'


class OrganizationDelete(OnlyForAdminsMixin, PermissionRequiredMixin,
                         AMYDeleteView):
    model = Organization
    slug_field = 'domain'
    slug_url_kwarg = 'org_domain'
    permission_required = 'workshops.delete_organization'
    success_url = reverse_lazy('all_organizations')


# ------------------------------------------------------------
# Membership related views
# ------------------------------------------------------------

class AllMemberships(OnlyForAdminsMixin, AMYListView):
    context_object_name = 'all_memberships'
    template_name = 'fiscal/all_memberships.html'
    filter_class = MembershipFilter
    queryset = Membership.objects.annotate(
        instructor_training_seats_total=(
            F('seats_instructor_training') +
            F('additional_instructor_training_seats')
        ),
        # for future reference, in case someone would want to implement
        # this annotation
        # instructor_training_seats_utilized=(
        #     Count('task', filter=Q(task__role__name='learner'))
        # ),
        instructor_training_seats_remaining=(
            F('seats_instructor_training') +
            F('additional_instructor_training_seats') -
            Count('task', filter=Q(task__role__name='learner'))
        ),
    )
    title = 'All Memberships'


class MembershipDetails(OnlyForAdminsMixin, AMYDetailView):
    prefetch_awards = Prefetch('person__award_set',
                               queryset=Award.objects.select_related('badge'))
    queryset = Membership.objects.select_related('organization') \
        .prefetch_related(
            Prefetch(
                'task_set',
                queryset=Task.objects.select_related('event', 'person')
                                     .prefetch_related(prefetch_awards)
            )
        )
    context_object_name = 'membership'
    template_name = 'fiscal/membership.html'
    pk_url_kwarg = 'membership_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '{0}'.format(self.object)
        return context


class MembershipCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                       PrepopulationSupportMixin, AMYCreateView):
    permission_required = [
        'workshops.add_membership',
        'workshops.change_organization',
    ]
    model = Membership
    form_class = MembershipCreateForm
    populate_fields = ['organization']


class MembershipUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                       RedirectSupportMixin, AMYUpdateView):
    permission_required = 'workshops.change_membership'
    model = Membership
    form_class = MembershipForm
    pk_url_kwarg = 'membership_id'
    template_name = 'generic_form_with_comments.html'


class MembershipDelete(OnlyForAdminsMixin, PermissionRequiredMixin,
                       AMYDeleteView):
    model = Membership
    permission_required = 'workshops.delete_membership'
    pk_url_kwarg = 'membership_id'

    def get_success_url(self):
        return reverse('organization_details', args=[
            self.get_object().organization.domain])


# ------------------------------------------------------------
# Sponsorship related views
# ------------------------------------------------------------

class SponsorshipCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                        AMYCreateView):
    model = Sponsorship
    permission_required = 'workshops.add_sponsorship'
    form_class = SponsorshipForm

    def get_success_url(self):
        return reverse('event_edit', args=[self.object.event.slug]) + \
            '#sponsors'


class SponsorshipDelete(OnlyForAdminsMixin, PermissionRequiredMixin,
                        AMYDeleteView):
    model = Sponsorship
    permission_required = 'workshops.delete_sponsorship'

    def get_success_url(self):
        return reverse('event_edit', args=[self.get_object().event.slug]) + \
            '#sponsors'
