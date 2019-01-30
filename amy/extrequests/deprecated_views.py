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
)
from extrequests.deprecated_filters import (
    EventRequestFilter,
    EventSubmissionFilter,
    DCSelfOrganizedEventRequestFilter,
)
from extrequests.models import (
    EventRequest,
    EventSubmission as EventSubmissionModel,
    DCSelfOrganizedEventRequest as DCSelfOrganizedEventRequestModel,
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
