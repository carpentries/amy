import csv
import datetime
from functools import partial
import io
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.core.exceptions import (
    ObjectDoesNotExist,
)
from django.db import (
    IntegrityError,
    transaction,
)
from django.db.models import (
    Prefetch,
    Q,
    ProtectedError,
)
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django_countries import countries
import django_rq
from requests.exceptions import HTTPError, RequestException

from autoemails.actions import SelfOrganisedRequestAction
from autoemails.base_views import ActionManageMixin
from autoemails.models import Trigger
from extrequests.filters import (
    TrainingRequestFilter,
    WorkshopRequestFilter,
    WorkshopInquiryFilter,
    SelfOrganisedSubmissionFilter,
)
from extrequests.forms import (
    MatchTrainingRequestForm,
    BulkMatchTrainingRequestForm,
    BulkChangeTrainingRequestForm,
    TrainingRequestUpdateForm,
    TrainingRequestsSelectionForm,
    TrainingRequestsMergeForm,
    WorkshopRequestAdminForm,
    WorkshopInquiryRequestAdminForm,
    SelfOrganisedSubmissionAdminForm,
)
from extrequests.models import (
    WorkshopInquiryRequest,
    SelfOrganisedSubmission,
)
from workshops.base_views import (
    AMYUpdateView,
    AMYListView,
    AMYDetailView,
    StateFilterMixin,
    RedirectSupportMixin,
    ChangeRequestStateView,
    AssignView,
)
from workshops.forms import (
    AdminLookupForm,
    BootstrapHelper,
    BulkUploadCSVForm,
    EventCreateForm,
)
from workshops.models import (
    TrainingRequest,
    WorkshopRequest,
    Tag,
    Task,
    Role,
    Person,
    Language,
    Curriculum,
    Organization,
)
from workshops.util import (
    OnlyForAdminsMixin,
    admin_required,
    redirect_with_next_support,
    upload_trainingrequest_manual_score_csv,
    clean_upload_trainingrequest_manual_score,
    update_manual_score,
    get_pagination_items,
    create_username,
    merge_objects,
    failed_to_delete,
    InternalError,
    fetch_workshop_metadata,
    parse_workshop_metadata,
    WrongWorkshopURL,
)

logger = logging.getLogger('amy.signals')
scheduler = django_rq.get_scheduler('default')
redis_connection = django_rq.get_connection('default')


# ------------------------------------------------------------
# WorkshopRequest related views
# ------------------------------------------------------------

class AllWorkshopRequests(OnlyForAdminsMixin, StateFilterMixin, AMYListView):
    context_object_name = 'requests'
    template_name = 'requests/all_workshoprequests.html'
    filter_class = WorkshopRequestFilter
    queryset = (
        WorkshopRequest.objects.select_related('assigned_to', 'institution')
                               .prefetch_related('requested_workshop_types')
    )
    title = 'Workshop requests'


class WorkshopRequestDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = WorkshopRequest.objects.all()
    context_object_name = 'object'
    template_name = 'requests/workshoprequest.html'
    pk_url_kwarg = 'request_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Workshop request #{}'.format(self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(
                initial={'person': self.object.assigned_to}
            )

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse('workshoprequest_assign',
                                args=[self.object.pk]),
            add_cancel_button=False)

        context['person_lookup_form'] = person_lookup_form
        return context


class WorkshopRequestChange(OnlyForAdminsMixin, PermissionRequiredMixin,
                            AMYUpdateView):
    permission_required = 'workshops.change_workshoprequest'
    model = WorkshopRequest
    pk_url_kwarg = 'request_id'
    form_class = WorkshopRequestAdminForm
    template_name = 'generic_form_with_comments.html'


class WorkshopRequestSetState(OnlyForAdminsMixin, ChangeRequestStateView):
    permission_required = 'workshops.change_workshoprequest'
    model = WorkshopRequest
    pk_url_kwarg = 'request_id'
    state_url_kwarg = 'state'
    permanent = False


@admin_required
@permission_required(['workshops.change_workshoprequest',
                      'workshops.add_event'],
                     raise_exception=True)
def workshoprequest_accept_event(request, request_id):
    """Accept event request by creating a new event."""
    wr = get_object_or_404(WorkshopRequest, state='p', pk=request_id)

    if request.method == 'POST':
        form = EventCreateForm(request.POST)

        if form.is_valid():
            event = form.save()

            person = wr.host()
            if person:
                Task.objects.create(event=event, person=person,
                                    role=Role.objects.get(name="host"))

            wr.state = 'a'
            wr.event = event
            wr.save()
            return redirect(reverse('event_details',
                                    args=[event.slug]))
        else:
            messages.error(request, 'Fix errors below.')

    else:
        # non-POST request
        form = EventCreateForm()

    context = {
        'object': wr,
        'form': form,
    }
    return render(request, 'requests/workshoprequest_accept_event.html',
                  context)


class WorkshopRequestAssign(OnlyForAdminsMixin, AssignView):
    permission_required = 'workshops.change_workshoprequest'
    model = WorkshopRequest
    pk_url_kwarg = 'request_id'
    person_url_kwarg = 'person_id'


# ------------------------------------------------------------
# WorkshopInquiryRequest related views
# ------------------------------------------------------------


class AllWorkshopInquiries(OnlyForAdminsMixin, StateFilterMixin, AMYListView):
    context_object_name = 'inquiries'
    template_name = 'requests/all_workshopinquiries.html'
    filter_class = WorkshopInquiryFilter
    queryset = (
        WorkshopInquiryRequest
            .objects.select_related('assigned_to', 'institution')
                    .prefetch_related('requested_workshop_types')
    )
    title = 'Workshop inquiries'


class WorkshopInquiryDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = WorkshopInquiryRequest.objects.all()
    context_object_name = 'object'
    template_name = 'requests/workshopinquiry.html'
    pk_url_kwarg = 'inquiry_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Workshop inquiry #{}'.format(self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(
                initial={'person': self.object.assigned_to}
            )

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse('workshopinquiry_assign',
                                args=[self.object.pk]),
            add_cancel_button=False)

        context['person_lookup_form'] = person_lookup_form
        return context


class WorkshopInquiryChange(OnlyForAdminsMixin, PermissionRequiredMixin,
                            AMYUpdateView):
    permission_required = 'extrequests.change_workshopinquiryrequest'
    model = WorkshopInquiryRequest
    pk_url_kwarg = 'inquiry_id'
    form_class = WorkshopInquiryRequestAdminForm
    template_name = 'generic_form_with_comments.html'


class WorkshopInquirySetState(OnlyForAdminsMixin, ChangeRequestStateView):
    permission_required = 'extrequests.change_workshopinquiryrequest'
    model = WorkshopInquiryRequest
    pk_url_kwarg = 'inquiry_id'
    state_url_kwarg = 'state'
    permanent = False


@admin_required
@permission_required(['extrequests.change_workshopinquiryrequest',
                      'workshops.add_event'],
                     raise_exception=True)
def workshopinquiry_accept_event(request, inquiry_id):
    """Accept workshop inquiry by creating a new event."""
    wr = get_object_or_404(WorkshopInquiryRequest, state='p', pk=inquiry_id)

    if request.method == 'POST':
        form = EventCreateForm(request.POST)

        if form.is_valid():
            event = form.save()

            person = wr.host()
            if person:
                Task.objects.create(event=event, person=person,
                                    role=Role.objects.get(name="host"))

            wr.state = 'a'
            wr.event = event
            wr.save()
            return redirect(reverse('event_details',
                                    args=[event.slug]))
        else:
            messages.error(request, 'Fix errors below.')

    else:
        # non-POST request
        form = EventCreateForm()

    context = {
        'object': wr,
        'form': form,
    }
    return render(request, 'requests/workshopinquiry_accept_event.html',
                  context)


class WorkshopInquiryAssign(OnlyForAdminsMixin, AssignView):
    permission_required = 'extrequests.change_workshopinquiryrequest'
    model = WorkshopInquiryRequest
    pk_url_kwarg = 'inquiry_id'
    person_url_kwarg = 'person_id'


# ------------------------------------------------------------
# SelfOrganisedSubmission related views
# ------------------------------------------------------------


class AllSelfOrganisedSubmissions(OnlyForAdminsMixin, StateFilterMixin,
                                  AMYListView):
    context_object_name = 'submissions'
    template_name = 'requests/all_selforganisedsubmissions.html'
    filter_class = SelfOrganisedSubmissionFilter
    queryset = (
        SelfOrganisedSubmission.objects.select_related('assigned_to',
                                                       'institution')
                                       .prefetch_related('workshop_types')
    )
    title = 'Self-Organised submissions'


class SelfOrganisedSubmissionDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = SelfOrganisedSubmission.objects.all()
    context_object_name = 'object'
    template_name = 'requests/selforganisedsubmission.html'
    pk_url_kwarg = 'submission_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Self-Organised submission #{}'.format(
            self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(
                initial={'person': self.object.assigned_to}
            )

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse('selforganisedsubmission_assign',
                                args=[self.object.pk]),
            add_cancel_button=False)

        context['person_lookup_form'] = person_lookup_form
        return context


class SelfOrganisedSubmissionChange(OnlyForAdminsMixin,
                                    PermissionRequiredMixin,
                                    AMYUpdateView):
    permission_required = 'extrequests.change_selforganisedsubmission'
    model = SelfOrganisedSubmission
    pk_url_kwarg = 'submission_id'
    form_class = SelfOrganisedSubmissionAdminForm
    template_name = 'generic_form_with_comments.html'


class SelfOrganisedSubmissionSetState(OnlyForAdminsMixin,
                                      ChangeRequestStateView):
    permission_required = 'extrequests.change_selforganisedsubmission'
    model = SelfOrganisedSubmission
    pk_url_kwarg = 'submission_id'
    state_url_kwarg = 'state'
    permanent = False


@admin_required
@permission_required(['extrequests.change_selforganisedsubmission',
                      'workshops.add_event'],
                     raise_exception=True)
def selforganisedsubmission_accept_event(request, submission_id):
    """Accept event request by creating a new event."""
    wr = get_object_or_404(SelfOrganisedSubmission, state='p',
                           pk=submission_id)

    mix_match = wr.workshop_types.filter(mix_match=True).exists()

    FormClass = partial(
        EventCreateForm,
        show_lessons=mix_match,
    )

    if request.method == 'POST':
        form = FormClass(request.POST)

        if form.is_valid():
            event = form.save()

            person = wr.host()
            if person:
                Task.objects.create(event=event, person=person,
                                    role=Role.objects.get(name="host"))

            wr.state = 'a'
            wr.event = event
            wr.save()

            if SelfOrganisedRequestAction.check(event):
                objs = dict(event=event, request=wr)
                jobs, rqjobs = ActionManageMixin.add(
                    action_class=SelfOrganisedRequestAction,
                    logger=logger,
                    scheduler=scheduler,
                    triggers=Trigger.objects.filter(
                        active=True, action="self-organised-request-form"
                    ),
                    context_objects=objs,
                    object_=event,
                    request=request,
                )

            return redirect(reverse('event_details',
                                    args=[event.slug]))
        else:
            messages.error(request, 'Fix errors below.')

    else:
        # non-POST request
        url = wr.workshop_url.strip()
        data = {
            'url': url,
            'curricula': list(wr.workshop_types.all()),
            'host': wr.host_organization() or wr.institution,
            'administrator': Organization.objects.get(domain='self-organized'),
        }
        if mix_match:
            data['tags'] = [Tag.objects.get(name='Circuits')]

        try:
            metadata = fetch_workshop_metadata(url)
            parsed_data = parse_workshop_metadata(metadata)
        except (AttributeError, HTTPError, RequestException, WrongWorkshopURL):
            # ignore errors, but show warning instead
            messages.warning(request, "Cannot automatically fill the form "
                                      "from provided workshop URL.")
        else:
            # keep working only if no exception occurred
            try:
                lang = parsed_data['language'].lower()
                parsed_data['language'] = Language.objects.get(subtag=lang)
            except (KeyError, ValueError, Language.DoesNotExist):
                # ignore non-existing
                messages.warning(request,
                                 "Cannot automatically fill language.")
                # it's easier to remove bad value than to leave
                # 500 Server Error when the form is rendered
                if 'language' in parsed_data:
                    del parsed_data['language']

            # even if for some reason language doesn't exist, we can push
            # an update
            data.update(parsed_data)

            if 'instructors' in data or 'helpers' in data:
                instructors = data.get('instructors') or ['none']
                helpers = data.get('helpers') or ['none']
                data['comment'] = "Instructors: {}\n\nHelpers: {}" \
                    .format(','.join(instructors), ','.join(helpers))

        # there's some data that we can push as initial for the form
        form = FormClass(initial=data)

    context = {
        'object': wr,
        'form': form,
    }
    return render(request,
                  'requests/selforganisedsubmission_accept_event.html',
                  context)


class SelfOrganisedSubmissionAssign(OnlyForAdminsMixin, AssignView):
    permission_required = 'extrequests.change_selforganisedsubmission'
    model = SelfOrganisedSubmission
    pk_url_kwarg = 'submission_id'
    person_url_kwarg = 'person_id'


# ------------------------------------------------------------
# TrainingRequest related views
# ------------------------------------------------------------

@admin_required
def all_trainingrequests(request):
    filter_ = TrainingRequestFilter(
        request.GET,
        queryset=TrainingRequest.objects.all().prefetch_related(
            Prefetch(
                'person__task_set',
                to_attr='training_tasks',
                queryset=Task.objects
                .filter(role__name='learner', event__tags__name='TTT')
                .select_related('event')
            ),
        )
    )

    form = BulkChangeTrainingRequestForm()
    match_form = BulkMatchTrainingRequestForm()

    if request.method == 'POST' and 'match' in request.POST:
        # Bulk match people associated with selected TrainingRequests to
        # trainings.
        match_form = BulkMatchTrainingRequestForm(request.POST)

        if match_form.is_valid():
            event = match_form.cleaned_data['event']
            member_site = match_form.cleaned_data['seat_membership']
            open_seat = match_form.cleaned_data['seat_open_training']

            # Perform bulk match
            for r in match_form.cleaned_data['requests']:
                # automatically accept this request
                r.state = 'a'
                r.save()

                # assign to an event
                Task.objects.get_or_create(
                    person=r.person,
                    role=Role.objects.get(name='learner'),
                    event=event,
                    seat_membership=member_site,
                    seat_open_training=open_seat,
                )

            requests_count = len(match_form.cleaned_data['requests'])
            today = datetime.date.today()

            if member_site:
                if (member_site.seats_instructor_training_remaining -
                        requests_count <= 0):
                    messages.warning(
                        request,
                        'Membership "{}" is using more training seats than '
                        "it's been allowed.".format(str(member_site)),
                    )

                # check if membership is active
                if not (member_site.agreement_start <= today <=
                        member_site.agreement_end):
                    messages.warning(
                        request,
                        'Membership "{}" is not active.'.format(
                            str(member_site))
                    )

                # show warning if training falls out of agreement dates
                if event.start and event.start < member_site.agreement_start \
                        or event.end and event.end > member_site.agreement_end:
                    messages.warning(
                        request,
                        'Training "{}" has start or end date outside '
                        'membership "{}" agreement dates.'.format(
                            str(event),
                            str(member_site),
                        ),
                    )

            messages.success(request, 'Successfully accepted and matched '
                                      'selected people to training.')

    elif request.method == 'POST' and 'accept' in request.POST:
        # Bulk discard selected TrainingRequests.
        form = BulkChangeTrainingRequestForm(request.POST)

        if form.is_valid():
            # Perform bulk discard
            for r in form.cleaned_data['requests']:
                r.state = 'a'
                r.save()

            messages.success(request, 'Successfully accepted selected '
                                      'requests.')

    elif request.method == 'POST' and 'discard' in request.POST:
        # Bulk discard selected TrainingRequests.
        form = BulkChangeTrainingRequestForm(request.POST)

        if form.is_valid():
            # Perform bulk discard
            for r in form.cleaned_data['requests']:
                r.state = 'd'
                r.save()

            messages.success(request, 'Successfully discarded selected '
                                      'requests.')

    elif request.method == 'POST' and 'unmatch' in request.POST:
        # Bulk unmatch people associated with selected TrainingRequests from
        # trainings.
        form = BulkChangeTrainingRequestForm(request.POST)

        form.check_person_matched = True
        if form.is_valid():
            # Perform bulk unmatch
            for r in form.cleaned_data['requests']:
                r.person.get_training_tasks().delete()

            messages.success(request, 'Successfully unmatched selected '
                                      'people from trainings.')

    context = {
        'title': 'Training Requests',
        'requests': filter_.qs,
        'filter': filter_,
        'form': form,
        'match_form': match_form,
    }

    return render(request, 'requests/all_trainingrequests.html', context)


@transaction.atomic
def _match_training_request_to_person(request, training_request, create=False,
                                      person=None):
    if create:
        try:
            training_request.person = Person.objects.create_user(
                username=create_username(training_request.personal,
                                         training_request.family),
                personal=training_request.personal,
                family=training_request.family,
                email=training_request.email,
            )
        except IntegrityError:
            # email address is not unique
            messages.error(request, 'Could not create a new person, because '
                                    'there already exists a person with '
                                    'exact email address.')
            return False

    else:
        training_request.person = person

    # as per #1270:
    # https://github.com/carpentries/amy/issues/1270#issuecomment-407515948
    # let's rewrite everything that's possible to rewrite
    try:
        training_request.person.personal = training_request.personal
        training_request.person.middle = training_request.middle
        training_request.person.family = training_request.family
        training_request.person.email = training_request.email
        training_request.person.secondary_email = \
            training_request.secondary_email
        training_request.person.country = training_request.country
        training_request.person.github = training_request.github
        training_request.person.affiliation = training_request.affiliation
        training_request.person.domains.set(training_request.domains.all())
        training_request.person.occupation = (
            training_request.get_occupation_display()
            if training_request.occupation else
            training_request.occupation_other)
        training_request.person.data_privacy_agreement = \
            training_request.data_privacy_agreement

        training_request.person.may_contact = True
        training_request.person.is_active = True

        training_request.person.save()
        training_request.person.synchronize_usersocialauth()
        training_request.save()

        messages.success(request, 'Request matched with the person.')

        return True
    except IntegrityError:
        # email or github not unique
        messages.warning(request, "It was impossible to update related "
                                  "person's data. Probably email address or "
                                  "Github handle used in the training request "
                                  "are not unique amongst person entries.")
        return False


@admin_required
def trainingrequest_details(request, pk):
    req = get_object_or_404(TrainingRequest, pk=int(pk))

    if request.method == 'POST':
        form = MatchTrainingRequestForm(request.POST)

        if form.is_valid():
            create = (form.action == "create")
            person = form.cleaned_data['person']
            ok = _match_training_request_to_person(request,
                                                   training_request=req,
                                                   create=create,
                                                   person=person)
            if ok:
                return redirect_with_next_support(
                    request, 'trainingrequest_details', req.pk)

    else:  # GET request
        # Provide initial value for form.person
        if req.person is not None:
            person = req.person
        else:
            # No person is matched to the TrainingRequest yet. Suggest a
            # person from existing records.
            primary_email = (
                Q(email__iexact=req.email) |
                Q(secondary_email__iexact=req.email)
            )
            # only match secondary email if there's one provided, otherwise
            # we could get false-positive matches for empty email.
            secondary_email = Q() if not req.secondary_email else (
                Q(email__iexact=req.secondary_email) |
                Q(secondary_email__iexact=req.secondary_email)
            )
            name = Q(
                personal__iexact=req.personal,
                middle__iexact=req.middle,
                family__iexact=req.family,
            )
            person = Person.objects \
                           .filter(primary_email | secondary_email | name) \
                           .first()  # may return None
        form = MatchTrainingRequestForm(initial={'person': person})

    context = {
        'title': 'Training request #{}'.format(req.pk),
        'req': req,
        'form': form,
    }
    return render(request, 'requests/trainingrequest.html', context)


class TrainingRequestUpdate(RedirectSupportMixin,
                            OnlyForAdminsMixin,
                            AMYUpdateView):
    model = TrainingRequest
    form_class = TrainingRequestUpdateForm
    template_name = 'generic_form_with_comments.html'


@admin_required
@permission_required(['workshops.delete_trainingrequest',
                      'workshops.change_trainingrequest'],
                     raise_exception=True)
def trainingrequests_merge(request):
    """Display two training requests side by side on GET and merge them on
    POST.

    If no requests are supplied via GET params, display event selection
    form."""
    obj_a_pk = request.GET.get('trainingrequest_a')
    obj_b_pk = request.GET.get('trainingrequest_b')

    if not obj_a_pk or not obj_b_pk:
        context = {
            'title': 'Select Training Requests to merge',
            'form': TrainingRequestsSelectionForm(),
        }
        return render(request, 'generic_form.html', context)

    obj_a = get_object_or_404(TrainingRequest, pk=obj_a_pk)
    obj_b = get_object_or_404(TrainingRequest, pk=obj_b_pk)

    form = TrainingRequestsMergeForm(initial=dict(trainingrequest_a=obj_a,
                                                  trainingrequest_b=obj_b))

    if request.method == "POST":
        form = TrainingRequestsMergeForm(request.POST)

        if form.is_valid():
            # merging in process
            data = form.cleaned_data

            obj_a = data['trainingrequest_a']
            obj_b = data['trainingrequest_b']

            # `base_obj` stays in the database after merge
            # `merging_obj` will be removed from DB after merge
            if data['id'] == 'obj_a':
                base_obj = obj_a
                merging_obj = obj_b
                base_a = True
            else:
                base_obj = obj_b
                merging_obj = obj_a
                base_a = False

            # non-M2M-relationships:
            easy = (
                'state', 'person', 'group_name', 'personal', 'middle',
                'family', 'email', 'secondary_email', 'github', 'occupation',
                'occupation_other',
                'affiliation', 'location', 'country', 'underresourced',
                'domains_other', 'underrepresented',
                'underrepresented_details', 'nonprofit_teaching_experience',
                'previous_training', 'previous_training_other',
                'previous_training_explanation', 'previous_experience',
                'previous_experience_other', 'previous_experience_explanation',
                'programming_language_usage_frequency',
                'teaching_frequency_expectation',
                'teaching_frequency_expectation_other',
                'max_travelling_frequency', 'max_travelling_frequency_other',
                'reason', 'user_notes', 'training_completion_agreement',
                'workshop_teaching_agreement',
                'data_privacy_agreement', 'code_of_conduct_agreement',
                'created_at', 'last_updated_at',
            )
            # M2M relationships
            difficult = (
                'domains', 'previous_involvement',
            )

            try:
                _, integrity_errors = merge_objects(obj_a, obj_b, easy,
                                                    difficult, choices=data,
                                                    base_a=base_a)

                if integrity_errors:
                    msg = ('There were integrity errors when merging related '
                           'objects:\n' '\n'.join(integrity_errors))
                    messages.warning(request, msg)

            except ProtectedError as e:
                return failed_to_delete(request, object=merging_obj,
                                        protected_objects=e.protected_objects)

            else:
                return redirect(base_obj.get_absolute_url())
        else:
            messages.error(request, 'Fix errors in the form.')

    context = {
        'title': 'Merge two training requets',
        'obj_a': obj_a,
        'obj_b': obj_b,
        'form': form,
    }
    return render(request, 'requests/trainingrequests_merge.html', context)


@admin_required
@permission_required(['workshops.change_trainingrequest'],
                     raise_exception=True)
def bulk_upload_training_request_scores(request):
    if request.method == "POST":
        form = BulkUploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            charset = request.FILES['file'].charset or settings.DEFAULT_CHARSET
            stream = io.TextIOWrapper(request.FILES['file'].file, charset)
            try:
                data = upload_trainingrequest_manual_score_csv(stream)
            except csv.Error as e:
                messages.error(
                    request,
                    "Error processing uploaded .CSV file: {}".format(e))
            except UnicodeDecodeError:
                messages.error(
                    request,
                    "Please provide a file in {} encoding."
                    .format(charset))
            else:
                request.session['bulk-upload-training-request-scores'] = data
                return redirect(
                    'bulk_upload_training_request_scores_confirmation'
                )

        else:
            messages.error(request, "Fix errors below.")

    else:
        form = BulkUploadCSVForm()

    context = {
        'title': 'Bulk upload Training Requests manual score',
        'form': form,
        'charset': settings.DEFAULT_CHARSET,
    }
    return render(
        request,
        'requests/trainingrequest_bulk_upload_manual_score_form.html',
        context,
    )


@admin_required
@permission_required(['workshops.change_trainingrequest'],
                     raise_exception=True)
def bulk_upload_training_request_scores_confirmation(request):
    """This view allows for verifying and saving of uploaded training
    request scores."""
    data = request.session.get('bulk-upload-training-request-scores')

    if not data:
        messages.warning(request,
                         "Could not locate CSV data, please upload again.")
        return redirect('bulk_upload_training_request_scores')

    if request.method == "POST":
        if (request.POST.get('confirm', None) and
                not request.POST.get('cancel', None)):

            errors, cleaned_data = \
                clean_upload_trainingrequest_manual_score(data)

            if not errors:
                try:
                    records_count = update_manual_score(cleaned_data)
                except (IntegrityError, ObjectDoesNotExist, InternalError,
                        TypeError, ValueError) as e:
                    messages.error(
                        request,
                        "Error saving data to the database: {}. Please make "
                        "sure to fix all errors listed below.".format(e)
                    )
                    errors, cleaned_data = \
                        clean_upload_trainingrequest_manual_score(data)
                else:
                    request.session['bulk-upload-training-request-scores'] = \
                        None
                    messages.success(
                        request,
                        "Successfully updated {} Training Requests."
                        .format(records_count)
                    )
                    return redirect('bulk_upload_training_request_scores')
            else:
                messages.warning(
                    request,
                    "Please fix the data according to error messages below.",
                )

        else:
            # any "cancel" or lack of "confirm" in POST cancels the upload
            request.session['bulk-upload-training-request-scores'] = None
            return redirect('bulk_upload_training_request_scores')

    else:
        errors, cleaned_data = clean_upload_trainingrequest_manual_score(data)
        if errors:
            messages.warning(
                request,
                'Please fix errors in the provided CSV file and re-upload.',
            )

    context = {
        'title': 'Confirm uploaded Training Requests manual score data',
        'any_errors': errors,
        'zipped': zip(cleaned_data, data),
    }
    return render(
        request,
        'requests/trainingrequest_bulk_upload_manual_score_confirmation.html',
        context,
    )
