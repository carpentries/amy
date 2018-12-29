from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.core.exceptions import (
    PermissionDenied,
)
from django.db import (
    IntegrityError,
    transaction,
)
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse

from extrequests.deprecated_forms import (
    SWCEventRequestNoCaptchaForm,
    DCEventRequestNoCaptchaForm,
    EventSubmitFormNoCaptcha,
    DCSelfOrganizedEventRequestFormNoCaptcha,
    ProfileUpdateRequestFormNoCaptcha,
    InvoiceRequestUpdateForm,
)
from extrequests.deprecated_filters import (
    EventRequestFilter,
    InvoiceRequestFilter,
    EventSubmissionFilter,
    DCSelfOrganizedEventRequestFilter,
)
from extrequests.models import (
    EventRequest,
    EventSubmission as EventSubmissionModel,
    DCSelfOrganizedEventRequest as DCSelfOrganizedEventRequestModel,
    ProfileUpdateRequest,
)
from workshops.base_views import (
    AMYUpdateView,
    AMYListView,
    AMYDetailView,
    StateFilterMixin,
    ChangeRequestStateView,
    AssignView,
)
from workshops.forms import (
    AdminLookupForm,
    BootstrapHelper,
    EventCreateForm,
    PersonLookupForm,
)
from workshops.models import (
    InvoiceRequest,
    Person,
    Award,
    Badge,
    Airport,
    Qualification,
)
from workshops.util import (
    OnlyForAdminsMixin,
    admin_required,
    create_username,
)


# ------------------------------------------------------------
# EventRequest related views
# CAUTION: THIS FEATURE IS DEPRECATED!!!
# ------------------------------------------------------------

class AllEventRequests(OnlyForAdminsMixin, StateFilterMixin, AMYListView):
    context_object_name = 'requests'
    template_name = 'requests_deprecated/all_eventrequests.html'
    filter_class = EventRequestFilter
    queryset = EventRequest.objects.select_related('assigned_to')
    title = 'SWC/DC Event requests'


class EventRequestDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = EventRequest.objects.all()
    context_object_name = 'object'
    template_name = 'requests_deprecated/eventrequest.html'
    pk_url_kwarg = 'request_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'SWC/DC Event request #{}'.format(
            self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(
                initial={'person': self.object.assigned_to}
            )

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse('eventrequest_assign', args=[self.object.pk]),
            add_cancel_button=False)

        context['person_lookup_form'] = person_lookup_form
        return context


class EventRequestChange(OnlyForAdminsMixin, PermissionRequiredMixin,
                         AMYUpdateView):
    permission_required = 'workshops.change_eventrequest'
    model = EventRequest
    pk_url_kwarg = 'request_id'

    def get_form_class(self):
        if self.object.workshop_type == 'swc':
            return SWCEventRequestNoCaptchaForm
        elif self.object.workshop_type == 'dc':
            return DCEventRequestNoCaptchaForm
        else:
            return None


class EventRequestSetState(OnlyForAdminsMixin, ChangeRequestStateView):
    permission_required = 'workshops.change_eventrequest'
    model = EventRequest
    pk_url_kwarg = 'request_id'
    state_url_kwarg = 'state'
    permanent = False


@admin_required
@permission_required(['workshops.change_eventrequest', 'workshops.add_event'],
                     raise_exception=True)
def eventrequest_accept_event(request, request_id):
    """Accept event request by creating a new event."""
    eventrequest = get_object_or_404(EventRequest, state='p', pk=request_id)
    form = EventCreateForm()

    if request.method == 'POST':
        form = EventCreateForm(request.POST)

        if form.is_valid():
            event = form.save()

            eventrequest.state = 'a'
            eventrequest.event = event
            eventrequest.save()
            return redirect(reverse('event_details',
                                    args=[event.slug]))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'object': eventrequest,
        'form': form,
    }
    return render(request, 'requests_deprecated/eventrequest_accept_event.html', context)


class EventRequestAssign(OnlyForAdminsMixin, AssignView):
    permission_required = 'workshops.change_eventrequest'
    model = EventRequest
    pk_url_kwarg = 'request_id'
    person_url_kwarg = 'person_id'


# ------------------------------------------------------------
# EventSubmission related views
# CAUTION: THIS FEATURE IS DEPRECATED!!!
# ------------------------------------------------------------

class AllEventSubmissions(OnlyForAdminsMixin, StateFilterMixin, AMYListView):
    context_object_name = 'submissions'
    template_name = 'requests_deprecated/all_eventsubmissions.html'
    filter_class = EventSubmissionFilter
    queryset = EventSubmissionModel.objects.all()
    title = 'Workshop submissions'


class EventSubmissionDetails(OnlyForAdminsMixin, AMYDetailView):
    context_object_name = 'object'
    template_name = 'requests_deprecated/eventsubmission.html'
    queryset = EventSubmissionModel.objects.all()
    pk_url_kwarg = 'submission_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Workshop submission #{}'.format(
            self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(
                initial={'person': self.object.assigned_to}
            )

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse('eventsubmission_assign',
                                args=[self.object.pk]))

        context['person_lookup_form'] = person_lookup_form
        return context


class EventSubmissionChange(OnlyForAdminsMixin, PermissionRequiredMixin,
                            AMYUpdateView):
    permission_required = 'workshops.change_eventsubmission'
    model = EventSubmissionModel
    form_class = EventSubmitFormNoCaptcha
    pk_url_kwarg = 'submission_id'


@admin_required
@permission_required(['workshops.change_eventsubmission',
                      'workshops.add_event'], raise_exception=True)
def eventsubmission_accept_event(request, submission_id):
    """Accept event submission by creating a new event."""
    submission = get_object_or_404(EventSubmissionModel, state='p',
                                   pk=submission_id)
    form = EventCreateForm()

    if request.method == 'POST':
        form = EventCreateForm(request.POST)

        if form.is_valid():
            event = form.save()

            submission.state = 'a'
            submission.event = event
            submission.save()
            return redirect(reverse('event_details',
                                    args=[event.slug]))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'object': submission,
        'form': form,
        'title': None,
    }
    return render(request, 'requests_deprecated/eventsubmission_accept_event.html',
                  context)


class EventSubmissionSetState(OnlyForAdminsMixin, ChangeRequestStateView):
    permission_required = 'workshops.change_eventsubmission'
    model = EventSubmissionModel
    pk_url_kwarg = 'submission_id'
    state_url_kwarg = 'state'
    permanent = False


class EventSubmissionAssign(OnlyForAdminsMixin, AssignView):
    permission_required = 'workshops.change_eventsubmission'
    model = EventSubmissionModel
    pk_url_kwarg = 'request_id'
    person_url_kwarg = 'person_id'


# ------------------------------------------------------------
# DCSelfOrganizedEventRequest related views
# CAUTION: THIS FEATURE IS DEPRECATED!!!
# ------------------------------------------------------------

class AllDCSelfOrganizedEventRequests(OnlyForAdminsMixin, StateFilterMixin,
                                      AMYListView):
    context_object_name = 'requests'
    template_name = 'requests_deprecated/all_dcselforganizedeventrequests.html'
    filter_class = DCSelfOrganizedEventRequestFilter
    queryset = DCSelfOrganizedEventRequestModel.objects.all()
    title = 'Data Carpentry self-organized workshop requests'


class DCSelfOrganizedEventRequestDetails(OnlyForAdminsMixin, AMYDetailView):
    context_object_name = 'object'
    template_name = 'requests_deprecated/dcselforganizedeventrequest.html'
    queryset = DCSelfOrganizedEventRequestModel.objects.all()
    pk_url_kwarg = 'request_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'DC self-organized workshop request #{}'.format(
            self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(
                initial={'person': self.object.assigned_to}
            )

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse('dcselforganizedeventrequest_assign',
                                args=[self.object.pk]))

        context['person_lookup_form'] = person_lookup_form
        return context


class DCSelfOrganizedEventRequestChange(OnlyForAdminsMixin,
                                        PermissionRequiredMixin,
                                        AMYUpdateView):
    permission_required = 'workshops.change_dcselforganizedeventrequest'
    model = DCSelfOrganizedEventRequestModel
    form_class = DCSelfOrganizedEventRequestFormNoCaptcha
    pk_url_kwarg = 'request_id'


class DCSelfOrganizedEventRequestSetState(OnlyForAdminsMixin,
                                          ChangeRequestStateView):
    permission_required = 'workshops.change_dcselforganizedeventrequest'
    model = DCSelfOrganizedEventRequestModel
    pk_url_kwarg = 'request_id'
    state_url_kwarg = 'state'
    permanent = False


@admin_required
@permission_required(['workshops.change_dcselforganizedeventrequest',
                      'workshops.add_event'],
                     raise_exception=True)
def dcselforganizedeventrequest_accept_event(request, request_id):
    """Accept DC self-org. event request by creating a new event."""
    event_req = get_object_or_404(DCSelfOrganizedEventRequestModel, state='p',
                                  pk=request_id)
    form = EventCreateForm()

    if request.method == 'POST':
        form = EventCreateForm(request.POST)

        if form.is_valid():
            event = form.save()

            event_req.state = 'a'
            event_req.event = event
            event_req.save()
            return redirect(reverse('event_details',
                                    args=[event.slug]))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'object': event_req,
        'form': form,
    }
    return render(request,
                  'requests_deprecated/dcselforganizedeventrequest_accept_event.html',
                  context)


class DCSelfOrganizedEventRequestAssign(OnlyForAdminsMixin, AssignView):
    permission_required = 'workshops.change_dcselforganizedeventrequest'
    model = DCSelfOrganizedEventRequestModel
    pk_url_kwarg = 'request_id'
    person_url_kwarg = 'person_id'


# ------------------------------------------------------------
# ProfileUpdateRequest related views
# CAUTION: THIS FEATURE IS DEPRECATED!!!
# ------------------------------------------------------------

class AllProfileUpdateRequests(OnlyForAdminsMixin, AMYListView):
    context_object_name = 'requests'
    template_name = 'requests_deprecated/all_profileupdaterequests.html'
    title = 'Instructor profile update requests'
    queryset = ProfileUpdateRequest.objects.filter(active=True) \
                                           .order_by('-created_at')
    active_requests = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_requests'] = self.active_requests
        return context


class AllClosedProfileUpdateRequests(AllProfileUpdateRequests):
    queryset = ProfileUpdateRequest.objects.filter(active=False) \
                                           .order_by('-created_at')
    active_requests = False


@admin_required
def profileupdaterequest_details(request, request_id):
    update_request = get_object_or_404(ProfileUpdateRequest,
                                       pk=request_id)

    person_selected = False

    person = None
    form = None

    # Nested lookup.
    # First check if there's person with the same email, then maybe check if
    # there's a person with the same first and last names.
    try:
        person = Person.objects.get(email=update_request.email)
    except Person.DoesNotExist:
        try:
            person = Person.objects.get(personal=update_request.personal,
                                        family=update_request.family)
        except (Person.DoesNotExist, Person.MultipleObjectsReturned):
            # Either none or multiple people with the same first and last
            # names.
            # But the user might have submitted some person by themselves. We
            # should check that!
            try:
                form = PersonLookupForm(request.GET)
                person = Person.objects.get(pk=int(request.GET['person']))
                person_selected = True
            except KeyError:
                person = None
                # if the form wasn't submitted, initialize it without any
                # input data
                form = PersonLookupForm()
            except (ValueError, Person.DoesNotExist):
                person = None

    if person:
        # check if the person has instructor badge
        person.has_instructor_badge = Award.objects.filter(
            badge__in=Badge.objects.instructor_badges(), person=person
        ).exists()

    try:
        airport = Airport.objects.get(iata__iexact=update_request.airport_iata)
    except Airport.DoesNotExist:
        airport = None

    context = {
        'title': ('Instructor profile update request #{}'
                  .format(update_request.pk)),
        'new': update_request,
        'old': person,
        'person_form': form,
        'person_selected': person_selected,
        'airport': airport,
    }
    return render(request, 'requests_deprecated/profileupdaterequest.html', context)


class ProfileUpdateRequestFix(OnlyForAdminsMixin, PermissionRequiredMixin,
                              AMYUpdateView):
    permission_required = 'workshops.change_profileupdaterequest'
    model = ProfileUpdateRequest
    form_class = ProfileUpdateRequestFormNoCaptcha
    pk_url_kwarg = 'request_id'


@admin_required
@permission_required('workshops.change_profileupdaterequest',
                     raise_exception=True)
def profileupdaterequest_discard(request, request_id):
    """Discard ProfileUpdateRequest, ie. set it to inactive."""
    profileupdate = get_object_or_404(ProfileUpdateRequest, active=True,
                                      pk=request_id)
    profileupdate.active = False
    profileupdate.save()

    messages.success(request,
                     'Profile update request was discarded successfully.')
    return redirect(reverse('all_profileupdaterequests'))


@admin_required
@permission_required('workshops.change_profileupdaterequest',
                     raise_exception=True)
def profileupdaterequest_accept(request, request_id, person_id=None):
    """
    Accept the profile update by rewriting values to selected user's profile.

    IMPORTANT: we do not rewrite all of the data users input (like
    other gender, or other lessons).  All of it is still in
    the database model ProfileUpdateRequest, but does not get written to the
    Person model object.
    """
    profileupdate = get_object_or_404(ProfileUpdateRequest, active=True,
                                      pk=request_id)
    airport = get_object_or_404(Airport,
                                iata__iexact=profileupdate.airport_iata)

    if person_id is None:
        person = Person()
        # since required perms change depending on `person_id`, we have to
        # check the perms programmatically; here user is required
        # `workshops.add_person` in order to add a new person
        if not request.user.has_perm('workshops.add_person'):
            raise PermissionDenied
    else:
        person = get_object_or_404(Person, pk=person_id)
        person_name = str(person)
        # since required perms change depending on `person_id`, we have to
        # check the perms programmatically; here user is required
        # `workshops.change_person` in order to set existing person's fields
        if not request.user.has_perm('workshops.change_person'):
            raise PermissionDenied

    person.personal = profileupdate.personal
    person.middle = profileupdate.middle
    person.family = profileupdate.family
    person.email = profileupdate.email
    person.affiliation = profileupdate.affiliation
    person.country = profileupdate.country
    person.airport = airport
    person.github = profileupdate.github
    person.twitter = profileupdate.twitter
    person.url = profileupdate.website
    # if occupation is "Other", simply save the `occupation_other` field,
    # otherwise get full display of occupation (since it's a choice field)
    if profileupdate.occupation == '':
        person.occupation = profileupdate.occupation_other
    else:
        person.occupation = profileupdate.get_occupation_display()
    person.orcid = profileupdate.orcid
    person.gender = profileupdate.gender
    person.user_notes = profileupdate.notes

    with transaction.atomic():
        # we need person to exist in the database in order to set domains and
        # lessons
        if not person.id:
            try:
                person.username = create_username(person.personal,
                                                  person.family)
                person.save()
            except IntegrityError:
                messages.error(
                    request,
                    'Cannot update profile: some database constraints weren\'t'
                    ' fulfilled. Make sure that user name, GitHub user name,'
                    ' Twitter user name, or email address are unique.'
                )
                return redirect(profileupdate.get_absolute_url())

        person.domains.set(list(profileupdate.domains.all()))
        person.languages.set(profileupdate.languages.all())

        try:
            person.save()
        except IntegrityError:
            messages.error(
                request,
                'Cannot update profile: some database constraints weren\'t'
                'fulfilled. Make sure that user name, GitHub user name,'
                'Twitter user name, or email address are unique.'
            )
            return redirect(profileupdate.get_absolute_url())

        # Since Person.lessons uses a intermediate model Qualification, we
        # ought to operate on Qualification objects instead of using
        # Person.lessons as a list.

        # erase old lessons
        Qualification.objects.filter(person=person).delete()
        # add new
        Qualification.objects.bulk_create([
            Qualification(person=person, lesson=L)
            for L in profileupdate.lessons.all()
        ])

        profileupdate.active = False
        profileupdate.save()

    if person_id is None:
        messages.success(request,
                         'New person was added successfully.')
    else:
        messages.success(request,
                         '{} was updated successfully.'.format(person_name))

    return redirect(person.get_absolute_url())


# ------------------------------------------------------------
# InvoiceRequest related views
# CAUTION: THIS FEATURE IS DEPRECATED!!!

class AllInvoiceRequests(OnlyForAdminsMixin, AMYListView):
    context_object_name = 'requests'
    template_name = 'requests_deprecated/all_invoicerequests.html'
    filter_class = InvoiceRequestFilter
    queryset = InvoiceRequest.objects.all()
    title = 'Invoice requests'

    def get_filter_data(self):
        data = self.request.GET.copy()
        data['status'] = data.get('status', '')
        return data


class InvoiceRequestDetails(OnlyForAdminsMixin, AMYDetailView):
    context_object_name = 'object'
    template_name = 'requests_deprecated/invoicerequest.html'
    queryset = InvoiceRequest.objects.all()
    pk_url_kwarg = 'request_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Invoice request #{}'.format(self.get_object().pk)
        return context


class InvoiceRequestUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                           AMYUpdateView):
    permission_required = 'workshops.change_invoicerequest'
    model = InvoiceRequest
    form_class = InvoiceRequestUpdateForm
    pk_url_kwarg = 'request_id'
