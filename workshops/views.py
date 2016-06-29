import csv
import datetime
import io
import re
from django.views.decorators.http import require_POST

import requests

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
)
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.http import HttpResponseBadRequest
from django.db import IntegrityError
from django.db.models import Count, Q, F, Model, ProtectedError, Sum
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import get_template
from django.views.generic import ListView, DetailView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, ModelFormMixin
from django.contrib.auth.decorators import permission_required
from github.GithubException import GithubException

from reversion.models import Revision
from reversion.revisions import get_for_object

from workshops import github_auth
from workshops.management.commands.check_for_workshop_websites_updates import (
    Command as WebsiteUpdatesCommand)
from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    Qualification,
    Person,
    Role,
    Host,
    Membership,
    Tag,
    Task,
    EventRequest,
    ProfileUpdateRequest,
    TodoItem,
    TodoItemQuerySet,
    InvoiceRequest,
    EventSubmission as EventSubmissionModel,
    TrainingRequest,
    DCSelfOrganizedEventRequest as DCSelfOrganizedEventRequestModel,
    is_admin)
from workshops.forms import (
    SearchForm, DebriefForm, WorkshopStaffForm, PersonForm, PersonBulkAddForm,
    EventForm, TaskForm, TaskFullForm, bootstrap_helper, bootstrap_helper_get,
    bootstrap_helper_with_add, BadgeAwardForm, PersonAwardForm,
    PersonPermissionsForm, bootstrap_helper_filter, PersonsSelectionForm,
    PersonTaskForm, HostForm, SWCEventRequestForm, DCEventRequestForm,
    ProfileUpdateRequestForm, PersonLookupForm, bootstrap_helper_wider_labels,
    SimpleTodoForm, bootstrap_helper_inline_formsets, BootstrapHelper,
    AdminLookupForm, ProfileUpdateRequestFormNoCaptcha, MembershipForm,
    TodoFormSet, EventsSelectionForm, EventsMergeForm, InvoiceRequestForm,
    InvoiceRequestUpdateForm, EventSubmitForm, EventSubmitFormNoCaptcha,
    PersonsMergeForm, PersonCreateForm,
    TrainingRequestForm, BootstrapHelperWiderLabels, AutoUpdateProfileForm,
    DCSelfOrganizedEventRequestForm, DCSelfOrganizedEventRequestFormNoCaptcha)
from workshops.util import (
    upload_person_task_csv, verify_upload_person_task,
    create_uploaded_persons_tasks, InternalError,
    update_event_attendance_from_tasks,
    WrongWorkshopURL,
    fetch_event_metadata,
    parse_metadata_from_event_website,
    validate_metadata_from_event_website,
    assignment_selection,
    get_pagination_items,
    Paginator,
    failed_to_delete,
    assign,
    merge_objects,
    create_username,
    admin_required,
    OnlyForAdminsMixin,
    login_required, login_not_required, LoginNotRequiredMixin)

from workshops.filters import (
    EventFilter, HostFilter, PersonFilter, TaskFilter, AirportFilter,
    EventRequestFilter, BadgeAwardsFilter, InvoiceRequestFilter,
    EventSubmissionFilter, DCSelfOrganizedEventRequestFilter,
)

from api.views import ReportsViewSet

# ------------------------------------------------------------


class CreateViewContext(SuccessMessageMixin, CreateView):
    """
    Class-based view for creating objects that extends default template context
    by adding model class used in objects creation.
    """
    success_message = '{name} was created successfully.'

    def get_context_data(self, **kwargs):
        context = super(CreateViewContext, self).get_context_data(**kwargs)

        # self.model is available in CreateView as the model class being
        # used to create new model instance
        context['model'] = self.model

        if self.model and issubclass(self.model, Model):
            context['title'] = 'New {}'.format(self.model._meta.verbose_name)
        else:
            context['title'] = 'New object'

        context['form_helper'] = bootstrap_helper
        return context

    def get_success_message(self, cleaned_data):
        "Format self.success_message, used by messages framework from Django."
        return self.success_message.format(cleaned_data, name=str(self.object))


class UpdateViewContext(SuccessMessageMixin, UpdateView):
    """
    Class-based view for updating objects that extends default template context
    by adding proper page title.
    """
    success_message = '{name} was updated successfully.'

    def get_context_data(self, **kwargs):
        context = super(UpdateViewContext, self).get_context_data(**kwargs)

        # self.model is available in UpdateView as the model class being
        # used to update model instance
        context['model'] = self.model

        context['view'] = self

        # self.object is available in UpdateView as the object being currently
        # edited
        context['title'] = str(self.object)

        context['form_helper'] = bootstrap_helper
        return context

    def get_success_message(self, cleaned_data):
        "Format self.success_message, used by messages framework from Django."
        return self.success_message.format(cleaned_data, name=str(self.object))


class FilteredListView(ListView):
    paginator_class = Paginator
    filter_class = None
    queryset = None

    def get_filter_data(self):
        """Datasource for the filter."""
        return self.request.GET

    def get_queryset(self):
        """Apply a filter to the queryset. Filter is compatible with pagination
        and queryset."""
        self.filter = self.filter_class(self.get_filter_data(),
                                        super().get_queryset())
        return self.filter

    def get_context_data(self, **kwargs):
        """Enhance context by adding a filter to it."""
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter
        context['form_helper'] = bootstrap_helper_filter
        return context


class EmailSendMixin():
    email_fail_silently = True
    email_kwargs = None

    def get_subject(self):
        """Generate email subject."""
        return ""

    def get_body(self):
        """Generate email body (in TXT and HTML versions)."""
        return "", ""

    def prepare_email(self):
        """Set up email contents."""
        subject = self.get_subject()
        body_txt, body_html = self.get_body()
        email = EmailMultiAlternatives(subject, body_txt,
                                       **self.email_kwargs)
        email.attach_alternative(body_html, 'text/html')
        return email

    def send_email(self, email):
        """Send a prepared email out."""
        return email.send(fail_silently=self.email_fail_silently)

    def form_valid(self, form):
        """Once form is valid, send the email."""
        results = super().form_valid(form)
        email = self.prepare_email()
        self.send_email(email)
        return results

#------------------------------------------------------------


@login_required
def dispatch(request):
    if request.user and is_admin(request.user):
        return redirect(reverse('admin-dashboard'))
    else:
        return redirect(reverse('trainee-dashboard'))


@admin_required
def admin_dashboard(request):
    """Home page for admins."""

    current_events = (
        Event.objects.upcoming_events() | Event.objects.ongoing_events()
    ).active()
    uninvoiced_events = Event.objects.active().uninvoiced_events()
    unpublished_events = Event.objects.active().unpublished_events() \
                                      .select_related('host')

    assigned_to, is_admin = assignment_selection(request)

    if assigned_to == 'me':
        current_events = current_events.filter(assigned_to=request.user)
        uninvoiced_events = uninvoiced_events.filter(assigned_to=request.user)
        unpublished_events = unpublished_events.filter(
            assigned_to=request.user)

    elif assigned_to == 'noone':
        current_events = current_events.filter(assigned_to__isnull=True)
        uninvoiced_events = uninvoiced_events.filter(
            assigned_to__isnull=True)
        unpublished_events = unpublished_events.filter(
            assigned_to__isnull=True)

    elif assigned_to == 'all':
        # no filtering
        pass

    else:
        # no filtering
        pass

    # assigned events that have unaccepted changes
    updated_metadata = Event.objects.active() \
                                    .filter(assigned_to=request.user) \
                                    .filter(metadata_changed=True) \
                                    .count()

    context = {
        'title': None,
        'is_admin': is_admin,
        'assigned_to': assigned_to,
        'current_events': current_events,
        'uninvoiced_events': uninvoiced_events,
        'unpublished_events': unpublished_events,
        'todos_start_date': TodoItemQuerySet.current_week_dates()[0],
        'todos_end_date': TodoItemQuerySet.next_week_dates()[1],
        'updated_metadata': updated_metadata,
    }
    return render(request, 'workshops/admin_dashboard.html', context)


@admin_required
def changes_log(request):
    log = Revision.objects.all().select_related('user') \
                                .prefetch_related('version_set') \
                                .order_by('-date_created')
    log = get_pagination_items(request, log)
    context = {
        'log': log
    }
    return render(request, 'workshops/changes_log.html', context)

#------------------------------------------------------------


@admin_required
def all_hosts(request):
    '''List all hosts.'''

    filter = HostFilter(request.GET, queryset=Host.objects.all())
    hosts = get_pagination_items(request, filter)
    context = {'title' : 'All Hosts',
               'all_hosts' : hosts,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_hosts.html', context)


@admin_required
def host_details(request, host_domain):
    '''List details of a particular host.'''
    host = get_object_or_404(Host, domain=host_domain)
    events = Event.objects.filter(host=host)
    context = {'title' : 'Host {0}'.format(host),
               'host' : host,
               'events' : events}
    return render(request, 'workshops/host.html', context)


class HostCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                 CreateViewContext):
    permission_required = 'workshops.add_host'
    model = Host
    form_class = HostForm
    template_name = 'workshops/generic_form.html'


class HostUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                 UpdateViewContext):
    permission_required = 'workshops.change_host'
    model = Host
    form_class = HostForm
    slug_field = 'domain'
    slug_url_kwarg = 'host_domain'
    template_name = 'workshops/generic_form.html'


@admin_required
@permission_required('workshops.delete_host', raise_exception=True)
def host_delete(request, host_domain):
    """Delete specific host."""
    try:
        host = get_object_or_404(Host, domain=host_domain)
        host.delete()
        messages.success(request, 'Host was deleted successfully.')
        return redirect(reverse('all_hosts'))
    except ProtectedError as e:
        return failed_to_delete(request, host, e.protected_objects)


@admin_required
@permission_required(['workshops.add_membership', 'workshops.change_host'],
                     raise_exception=True)
def membership_create(request, host_domain):
    host = get_object_or_404(Host, domain=host_domain)
    form = MembershipForm(initial={'host': host})

    if request.method == "POST":
        form = MembershipForm(request.POST)
        if form.is_valid():
            form.save()

            messages.success(request,
                             'Membership was successfully added to the host')

            return redirect(reverse('host_details', args=[host.domain]))

    context = {
        'title': 'New membership for host {}'.format(host),
        'form': form,
        'form_helper': bootstrap_helper,
    }
    return render(request, 'workshops/generic_form.html', context)


class MembershipUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                       UpdateViewContext):
    permission_required = 'workshops.change_membership'
    model = Membership
    form_class = MembershipForm
    pk_url_kwarg = 'membership_id'
    template_name = 'workshops/generic_form.html'

    def get_success_url(self):
        return reverse('host_details', args=[self.object.host.domain])


@admin_required
@permission_required('workshops.delete_membership', raise_exception=True)
def membership_delete(request, membership_id):
    """Delete specific membership."""
    try:
        membership = get_object_or_404(Membership, pk=membership_id)
        host = membership.host
        membership.delete()
        messages.success(request, 'Membership was deleted successfully.')
        return redirect(reverse('host_details', args=[host.domain]))
    except ProtectedError as e:
        return failed_to_delete(request, host, e.protected_objects)


#------------------------------------------------------------

AIRPORT_FIELDS = ['iata', 'fullname', 'country', 'latitude', 'longitude']


@admin_required
def all_airports(request):
    '''List all airports.'''
    filter = AirportFilter(request.GET, queryset=Airport.objects.all())
    airports = get_pagination_items(request, filter)
    context = {'title' : 'All Airports',
               'all_airports' : airports,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_airports.html', context)


@admin_required
def airport_details(request, airport_iata):
    '''List details of a particular airport.'''
    airport = get_object_or_404(Airport, iata=airport_iata)
    context = {'title' : 'Airport {0}'.format(airport),
               'airport' : airport}
    return render(request, 'workshops/airport.html', context)


class AirportCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                    CreateViewContext):
    permission_required = 'workshops.add_airport'
    model = Airport
    fields = AIRPORT_FIELDS
    template_name = 'workshops/generic_form.html'


class AirportUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                    UpdateViewContext):
    permission_required = 'workshops.change_airport'
    model = Airport
    fields = AIRPORT_FIELDS
    slug_field = 'iata'
    slug_url_kwarg = 'airport_iata'
    template_name = 'workshops/generic_form.html'


@admin_required
@permission_required('workshops.delete_airport', raise_exception=True)
def airport_delete(request, airport_iata):
    """Delete specific airport."""
    try:
        airport = get_object_or_404(Airport, iata=airport_iata)
        airport.delete()
        messages.success(request, 'Airport was deleted successfully.')
        return redirect(reverse('all_airports'))
    except ProtectedError as e:
        return failed_to_delete(request, airport, e.protected_objects)

#------------------------------------------------------------


@admin_required
def all_persons(request):
    '''List all persons.'''

    filter = PersonFilter(
        request.GET,
        # notes are too large, so we defer them
        queryset=Person.objects.defer('notes').annotate(
            is_swc_instructor=Sum(Case(When(badges__name='swc-instructor',
                                            then=1),
                                       default=0,
                                       output_field=IntegerField())),
            is_dc_instructor=Sum(Case(When(badges__name='dc-instructor',
                                           then=1),
                                      default=0,
                                      output_field=IntegerField())),
        )
    )
    persons = get_pagination_items(request, filter)

    context = {'title' : 'All Persons',
               'all_persons' : persons,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_persons.html', context)


@admin_required
def person_details(request, person_id):
    '''List details of a particular person.'''
    try:
        person = Person.objects.annotate(
            num_taught=Count(
                Case(
                    When(task__role__name='instructor', then=Value(1)),
                    output_field=IntegerField()
                )
            ),
            num_helper=Count(
                Case(
                    When(task__role__name='helper', then=Value(1)),
                    output_field=IntegerField()
                )
            ),
            num_learner=Count(
                Case(
                    When(task__role__name='learner', then=Value(1)),
                    output_field=IntegerField()
                )
            )
        ).get(id=person_id)
    except Person.DoesNotExist:
        raise Http404('Person matching query does not exist.')
    awards = person.award_set.all()
    tasks = person.task_set.all()
    lessons = person.lessons.all()
    domains = person.domains.all()
    languages = person.languages.all()

    try:
        is_usersocialauth_in_sync = person.check_if_usersocialauth_is_in_sync()
    except GithubException:
        is_usersocialauth_in_sync = 'unknown'

    context = {
        'title': 'Person {0}'.format(person),
        'person': person,
        'awards': awards,
        'tasks': tasks,
        'lessons': lessons,
        'domains': domains,
        'languages': languages,
        'is_usersocialauth_in_sync': is_usersocialauth_in_sync,
    }
    return render(request, 'workshops/person.html', context)


@admin_required
def person_bulk_add_template(request):
    ''' Dynamically generate a CSV template that can be used to bulk-upload
    people.

    See https://docs.djangoproject.com/en/1.7/howto/outputting-csv/#using-the-python-csv-library
    '''
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=BulkPersonAddTemplate.csv'

    writer = csv.writer(response)
    writer.writerow(Person.PERSON_TASK_UPLOAD_FIELDS)
    return response


@admin_required
@permission_required('workshops.add_person', raise_exception=True)
def person_bulk_add(request):
    if request.method == 'POST':
        form = PersonBulkAddForm(request.POST, request.FILES)
        if form.is_valid():
            charset = request.FILES['file'].charset or settings.DEFAULT_CHARSET
            stream = io.TextIOWrapper(request.FILES['file'].file, charset)
            try:
                persons_tasks, empty_fields = upload_person_task_csv(stream)
            except csv.Error as e:
                messages.add_message(
                    request, messages.ERROR,
                    "Error processing uploaded .CSV file: {}".format(e))
            except UnicodeDecodeError as e:
                messages.add_message(
                    request, messages.ERROR,
                    "Please provide a file in {} encoding."
                    .format(charset))
            else:
                if empty_fields:
                    msg_template = ("The following required fields were not"
                                    " found in the uploaded file: {}")
                    msg = msg_template.format(', '.join(empty_fields))
                    messages.add_message(request, messages.ERROR, msg)
                else:
                    # instead of insta-saving, put everything into session
                    # then redirect to confirmation page which in turn saves
                    # the data
                    request.session['bulk-add-people'] = persons_tasks
                    return redirect('person_bulk_add_confirmation')

    else:
        form = PersonBulkAddForm()

    context = {
        'title': 'Bulk Add People',
        'form': form,
        'charset': settings.DEFAULT_CHARSET,
    }
    return render(request, 'workshops/person_bulk_add_form.html', context)


@admin_required
@permission_required('workshops.add_person', raise_exception=True)
def person_bulk_add_confirmation(request):
    """
    This view allows for manipulating and saving session-stored upload data.
    """
    persons_tasks = request.session.get('bulk-add-people')

    # if the session is empty, add message and redirect
    if not persons_tasks:
        messages.warning(request, "Could not locate CSV data, please try the upload again.")
        return redirect('person_bulk_add')

    if request.method == 'POST':
        # update values if user wants to change them
        personals = request.POST.getlist("personal")
        families = request.POST.getlist("family")
        usernames = request.POST.getlist("username")
        emails = request.POST.getlist("email")
        events = request.POST.getlist("event")
        roles = request.POST.getlist("role")
        data_update = zip(personals, families, usernames, emails, events,
                          roles)
        for k, record in enumerate(data_update):
            personal, family, username, email, event, role = record
            # "field or None" converts empty strings to None values
            persons_tasks[k] = {
                'personal': personal,
                'family': family,
                'username': username,
                'email': email or None
            }
            # when user wants to drop related event they will send empty string
            # so we should unconditionally accept new value for event even if
            # it's an empty string
            persons_tasks[k]['event'] = event
            persons_tasks[k]['role'] = role
            persons_tasks[k]['errors'] = None  # reset here

        # save updated data to the session
        request.session['bulk-add-people'] = persons_tasks

        # check if user wants to verify or save, or cancel
        if request.POST.get('verify', None):
            # if there's "verify" in POST, then do only verification
            any_errors = verify_upload_person_task(persons_tasks)
            if any_errors:
                messages.add_message(request, messages.ERROR,
                                     "Please make sure to fix all errors "
                                     "listed below.")

            context = {'title': 'Confirm uploaded data',
                       'persons_tasks': persons_tasks,
                       'any_errors': any_errors}
            return render(request, 'workshops/person_bulk_add_results.html',
                          context)

        # there must be "confirm" and no "cancel" in POST in order to save
        elif (request.POST.get('confirm', None) and
              not request.POST.get('cancel', None)):
            try:
                # verification now makes something more than database
                # constraints so we should call it first
                verify_upload_person_task(persons_tasks)
                persons_created, tasks_created = \
                    create_uploaded_persons_tasks(persons_tasks)
            except (IntegrityError, ObjectDoesNotExist, InternalError) as e:
                messages.add_message(request, messages.ERROR,
                                     "Error saving data to the database: {}. "
                                     "Please make sure to fix all errors "
                                     "listed below.".format(e))
                any_errors = verify_upload_person_task(persons_tasks)
                context = {'title': 'Confirm uploaded data',
                           'persons_tasks': persons_tasks,
                           'any_errors': any_errors}
                return render(request,
                              'workshops/person_bulk_add_results.html',
                              context, status=400)

            else:
                request.session['bulk-add-people'] = None
                messages.add_message(
                    request, messages.SUCCESS,
                    'Successfully created {0} persons and {1} tasks.'
                    .format(len(persons_created), len(tasks_created))
                )
                return redirect('person_bulk_add')

        else:
            # any "cancel" or no "confirm" in POST cancels the upload
            request.session['bulk-add-people'] = None
            return redirect('person_bulk_add')

    else:
        # alters persons_tasks via reference
        any_errors = verify_upload_person_task(persons_tasks)

        context = {'title': 'Confirm uploaded data',
                   'persons_tasks': persons_tasks,
                   'any_errors': any_errors}
        return render(request, 'workshops/person_bulk_add_results.html',
                      context)


class PersonCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                   CreateViewContext):
    permission_required = 'workshops.add_person'
    model = Person
    form_class = PersonCreateForm
    template_name = 'workshops/generic_form.html'

    def form_valid(self, form):
        """Person.lessons uses an intermediary model so we need to manually add
        objects of that model.

        See more here: http://stackoverflow.com/a/15745652"""
        self.object = form.save(commit=False)  # don't save M2M fields

        self.object.username = create_username(
            personal=form.cleaned_data['personal'],
            family=form.cleaned_data['family'])

        # Need to save that object because of commit=False previously.
        # This doesn't save our troublesome M2M field.
        self.object.save()

        # saving intermediary M2M model: Qualification
        for lesson in form.cleaned_data['lessons']:
            Qualification.objects.create(lesson=lesson, person=self.object)

        # Important: we need to use ModelFormMixin.form_valid() here!
        # But by doing so we omit SuccessMessageMixin completely, so we need to
        # simulate it.  The code below is almost identical to
        # SuccessMessageMixin.form_valid().
        response = super(ModelFormMixin, self).form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response


@admin_required
@permission_required(['workshops.change_person', 'workshops.add_award',
                      'workshops.add_task'],
                     raise_exception=True)
def person_edit(request, person_id):
    person = get_object_or_404(Person, id=person_id)
    awards = person.award_set.order_by('badge__name')
    tasks = person.task_set.order_by('-event__slug')

    person_form = PersonForm(prefix='person', instance=person)
    award_form = PersonAwardForm(prefix='award', initial={
        'awarded': datetime.date.today(),
        'person': person,
    })
    task_form = PersonTaskForm(prefix='task', initial={'person': person})

    if request.method == 'POST':
        # check which form was submitted
        if 'award-badge' in request.POST:
            award_form = PersonAwardForm(request.POST, prefix='award')

            if award_form.is_valid():
                award = award_form.save()

                messages.success(
                    request,
                    '{person} was awarded {badge} badge.'.format(
                        person=str(person),
                        badge=award.badge.title,
                    ),
                    extra_tags='awards',
                )

                # to reset the form values
                return redirect(request.path)

            else:
                messages.error(request, 'Fix errors in the award form.',
                               extra_tags='awards')

        elif 'task-role' in request.POST:
            task_form = PersonTaskForm(request.POST, prefix='task')

            if task_form.is_valid():
                task = task_form.save()

                messages.success(
                    request,
                    '{person} was added a role {role} during {event} event.'
                    .format(
                        person=str(person),
                        role=task.role.name,
                        event=task.event.slug,
                    ),
                    extra_tags='tasks',
                )

                # to reset the form values
                return redirect(request.path)

            else:
                messages.error(request, 'Fix errors in the task form.',
                               extra_tags='tasks')

        else:
            person_form = PersonForm(request.POST, prefix='person',
                                     instance=person)
            if person_form.is_valid():
                lessons = person_form.cleaned_data['lessons']

                # remove existing Qualifications for user
                Qualification.objects.filter(person=person).delete()

                # add new Qualifications
                for lesson in lessons:
                    Qualification.objects.create(person=person, lesson=lesson)

                # don't save related lessons
                del person_form.cleaned_data['lessons']

                person = person_form.save()

                messages.success(
                    request,
                    '{name} was updated successfully.'.format(
                        name=str(person),
                    ),
                )

                return redirect(person)

            else:
                messages.error(request, 'Fix errors below.')

    # two separate forms on one page
    context = {'title': 'Edit Person {0}'.format(str(person)),
               'person_form': person_form,
               'object': person,
               'model': Person,
               'awards': awards,
               'award_form': award_form,
               'tasks': tasks,
               'task_form': task_form,
               'form_helper': bootstrap_helper,
               'form_helper_with_add': bootstrap_helper_with_add,
               }
    return render(request, 'workshops/person_edit_form.html', context)


@admin_required
@permission_required('workshops.delete_person', raise_exception=True)
def person_delete(request, person_id):
    """Delete specific person."""
    try:
        person = get_object_or_404(Person, pk=person_id)
        person.delete()

        messages.success(request, 'Person was deleted successfully.')
        return redirect(reverse('all_persons'))
    except ProtectedError as e:
        return failed_to_delete(request, person, e.protected_objects)


class PersonPermissions(OnlyForAdminsMixin, PermissionRequiredMixin,
                        UpdateViewContext):
    permission_required = 'workshops.change_person'
    model = Person
    form_class = PersonPermissionsForm
    pk_url_kwarg = 'person_id'
    template_name = 'workshops/generic_form.html'


@admin_required
def person_password(request, person_id):
    user = get_object_or_404(Person, pk=person_id)

    # Either the user requests change of their own password, or someone with
    # permission for changing person does.
    if not ((request.user == user) or
            (request.user.has_perm('workshops.change_person'))):
        raise PermissionDenied

    Form = PasswordChangeForm
    if request.user.is_superuser:
        Form = SetPasswordForm
    elif request.user.pk != user.pk:
        # non-superuser can only change their own password, not someone else's
        raise PermissionDenied

    if request.method == 'POST':
        form = Form(user, request.POST)
        if form.is_valid():
            form.save()  # saves the password for the user

            update_session_auth_hash(request, form.user)

            messages.success(request, 'Password was changed successfully.')

            return redirect(reverse('person_details', args=[user.id]))

        else:
            messages.error(request, 'Fix errors below.')
    else:
        form = Form(user)

    return render(request, 'workshops/generic_form.html', {
        'form': form,
        'model': Person,
        'object': user,
        'form_helper': bootstrap_helper,
        'title': 'Change password',
    })


@admin_required
@permission_required(['workshops.delete_person', 'workshops.change_person'],
                     raise_exception=True)
def persons_merge(request):
    """Display two persons side by side on GET and merge them on POST.

    If no persons are supplied via GET params, display person selection
    form."""
    obj_a_pk = request.GET.get('person_a_1')
    obj_b_pk = request.GET.get('person_b_1')

    if not obj_a_pk or not obj_b_pk:
        context = {
            'title': 'Merge Persons',
            'form': PersonsSelectionForm(),
            'form_helper': bootstrap_helper_get,
        }
        return render(request, 'workshops/merge_form.html', context)

    obj_a = get_object_or_404(Person, pk=obj_a_pk)
    obj_b = get_object_or_404(Person, pk=obj_b_pk)

    form = PersonsMergeForm(initial=dict(person_a=obj_a, person_b=obj_b))

    if request.method == 'POST':
        form = PersonsMergeForm(request.POST)

        if form.is_valid():
            # merging in process
            data = form.cleaned_data

            obj_a = data['person_a']
            obj_b = data['person_b']

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

            # non-M2M-relationships
            easy = (
                'username', 'personal', 'middle', 'family', 'email',
                'may_contact', 'gender', 'airport', 'github', 'twitter',
                'url', 'notes', 'affiliation', 'occupation', 'orcid',
                'is_active',
            )

            # M2M relationships
            difficult = ('award_set', 'qualification_set', 'domains',
                         'languages', 'task_set')

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

    context = {
        'title': 'Merge two persons',
        'form': form,
        'obj_a': obj_a,
        'obj_b': obj_b,
    }
    return render(request, 'workshops/persons_merge.html', context)


@admin_required
def sync_usersocialauth(request, person_id):
    person_id = int(person_id)
    try:
        person = Person.objects.get(pk=person_id)
    except Person.DoesNotExist:
        messages.error(request,
                       'Cannot sync UserSocialAuth table for person #{} '
                       '-- there is no Person with such id.'.format(person_id))
        return redirect(reverse('persons'))
    else:
        try:
            person.synchronize_usersocialauth()
        except GithubException:
            messages.error(request,
                           'Cannot sync UserSocialAuth table for person #{} '
                           'due to errors with GitHub API.'.format(person_id))
        else:
            messages.success(request, 'Sync UserSocialAuth successfully.')
        finally:
            return redirect(reverse('person_details', args=(person_id,)))

#------------------------------------------------------------

@admin_required
def all_events(request):
    '''List all events.'''
    filter = EventFilter(
        request.GET,
        queryset=Event.objects.all().defer('notes')  # notes are too large
                                    .prefetch_related('host', 'tags'),
    )
    events = get_pagination_items(request, filter)
    context = {'title' : 'All Events',
               'all_events' : events,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_events.html', context)


@admin_required
def event_details(request, event_ident):
    '''List details of a particular event.'''
    try:
        event = Event.get_by_ident(event_ident)
    except Event.DoesNotExist:
        raise Http404('Event matching query does not exist.')

    tasks = Task.objects \
                .filter(event__id=event.id) \
                .select_related('person', 'role') \
                .annotate(person_is_swc_instructor=Sum(
                              Case(When(person__badges__name='swc-instructor',
                                        then=1),
                                   default=0,
                                   output_field=IntegerField())),
                          person_is_dc_instructor=Sum(
                              Case(When(person__badges__name='dc-instructor',
                                        then=1),
                                   default=0,
                                   output_field=IntegerField()))) \
                .order_by('role__name')
    todos = event.todoitem_set.all()
    todo_form = SimpleTodoForm(prefix='todo', initial={
        'event': event,
    })

    if request.method == "POST" and request.user.has_perm('workshops.add_todoitem'):
        # Create ToDo items on todo_form submission only when user has permission
        todo_form = SimpleTodoForm(request.POST, prefix='todo', initial={
            'event': event,
        })
        if todo_form.is_valid():
            todo = todo_form.save()

            messages.success(
                request,
                'New TODO {todo} was added to the event {event}.'.format(
                    todo=str(todo),
                    event=event.get_ident(),
                ),
                extra_tags='newtodo',
            )
            return redirect(reverse(event_details, args=[event_ident, ]))
        else:
            messages.error(request, 'Fix errors in the TODO form.',
                           extra_tags='todos')

    person_lookup_form = AdminLookupForm()
    if event.assigned_to:
        person_lookup_form = AdminLookupForm(
            initial={'person': event.assigned_to}
        )

    person_lookup_helper = BootstrapHelper()
    person_lookup_helper.form_action = reverse('event_assign',
                                               args=[event_ident])
    context = {
        'title': 'Event {0}'.format(event),
        'event': event,
        'tasks': tasks,
        'todo_form': todo_form,
        'todos': todos,
        'all_emails' : tasks.filter(person__may_contact=True)\
            .exclude(person__email=None)\
            .values_list('person__email', flat=True),
        'helper': bootstrap_helper,
        'today': datetime.date.today(),
        'person_lookup_form': person_lookup_form,
        'person_lookup_helper': person_lookup_helper,
    }
    return render(request, 'workshops/event.html', context)


@admin_required
def validate_event(request, event_ident):
    '''Check the event's home page *or* the specified URL (for testing).'''
    try:
        event = Event.get_by_ident(event_ident)
    except Event.DoesNotExist:
        raise Http404('Event matching query does not exist.')

    page_url = request.GET.get('url', None)  # for manual override
    if page_url is None:
        page_url = event.url

    page_url = page_url.strip()

    error_messages = []

    try:
        metadata = fetch_event_metadata(page_url)
        # validate metadata
        error_messages = validate_metadata_from_event_website(metadata)

    except WrongWorkshopURL as e:
        error_messages.append(str(e))

    except requests.exceptions.HTTPError as e:
        error_messages.append(
            'Request for "{0}" returned status code {1}'
            .format(page_url, e.response.status_code)
        )

    except (requests.exceptions.ConnectionError,
            requests.exceptions.Timeout):
        error_messages.append("Network connection error.")

    context = {
        'title': 'Validate Event {0}'.format(event),
        'event': event,
        'page': page_url,
        'error_messages': error_messages,
    }
    return render(request, 'workshops/validate_event.html', context)


class EventCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                  CreateViewContext):
    permission_required = 'workshops.add_event'
    model = Event
    form_class = EventForm
    template_name = 'workshops/event_create_form.html'


@admin_required
@permission_required(['workshops.change_event', 'workshops.add_task'],
                     raise_exception=True)
def event_edit(request, event_ident):
    try:
        event = Event.get_by_ident(event_ident)
        tasks = event.task_set.order_by('role__name')
    except ObjectDoesNotExist:
        raise Http404("No event found matching the query.")

    event_form = EventForm(prefix='event', instance=event)
    task_form = TaskForm(prefix='task', initial={
        'event': event,
    })

    if request.method == 'POST':
        # check which form was submitted
        if "task-role" in request.POST:
            task_form = TaskForm(request.POST, prefix='task')

            if task_form.is_valid():
                task = task_form.save()

                messages.success(
                    request,
                    '{event} was added a new task "{task}".'.format(
                        event=str(event),
                        task=str(task),
                    ),
                )

                # if event.attendance is lower than number of learners, then
                # update the attendance
                update_event_attendance_from_tasks(event)

                # to reset the form values
                return redirect(request.path)

            else:
                messages.error(request, 'Fix errors below.')

        else:
            event_form = EventForm(request.POST, prefix='event',
                                   instance=event)
            if event_form.is_valid():
                event = event_form.save()

                messages.success(
                    request,
                    '{name} was updated successfully.'.format(
                        name=str(event),
                    ),
                )

                # if event.attendance is lower than number of learners, then
                # update the attendance
                update_event_attendance_from_tasks(event)

                return redirect(event)

            else:
                messages.error(request, 'Fix errors below.')

    context = {'title': 'Edit Event {0}'.format(event.get_ident()),
               'event_form': event_form,
               'object': event,
               'model': Event,
               'tasks': tasks,
               'task_form': task_form,
               'form_helper': bootstrap_helper,
               'form_helper_with_add': bootstrap_helper_with_add,
               }
    return render(request, 'workshops/event_edit_form.html', context)


@admin_required
@permission_required('workshops.delete_event', raise_exception=True)
def event_delete(request, event_ident):
    """Delete event, its tasks and related awards."""
    try:
        event = Event.get_by_ident(event_ident)
        event.delete()

        messages.success(request,
                         'Event and its tasks were deleted successfully.')
        return redirect(reverse('all_events'))
    except ObjectDoesNotExist:
        raise Http404("No event found matching the query.")
    except ProtectedError as e:
        return failed_to_delete(request, event, e.protected_objects)


@admin_required
def event_import(request):
    """Read metadata from remote URL and return them as JSON.

    This is used to read metadata from workshop website and then fill up fields
    on event_create form."""

    # TODO: remove POST support completely
    url = request.POST.get('url', '').strip()
    if not url:
        url = request.GET.get('url', '').strip()

    try:
        metadata = fetch_event_metadata(url)
        # normalize the metadata
        metadata = parse_metadata_from_event_website(metadata)
        return JsonResponse(metadata)

    except requests.exceptions.HTTPError as e:
        return HttpResponseBadRequest(
            'Request for "{0}" returned status code {1}.'
            .format(url, e.response.status_code)
        )

    except requests.exceptions.RequestException:
        return HttpResponseBadRequest('Network connection error.')

    except WrongWorkshopURL as e:
        return HttpResponseBadRequest(str(e))

    except KeyError:
        return HttpResponseBadRequest('Missing or wrong "url" parameter.')


@admin_required
@permission_required('workshops.change_event', raise_exception=True)
def event_assign(request, event_ident, person_id=None):
    """Set event.assigned_to. See `assign` docstring for more information."""
    try:
        event = Event.get_by_ident(event_ident)

        assign(request, event, person_id)

        return redirect(reverse('event_details', args=[event.get_ident()]))

    except Event.DoesNotExist:
        raise Http404("No event found matching the query.")


@admin_required
@permission_required(['workshops.delete_event', 'workshops.change_event'],
                     raise_exception=True)
def events_merge(request):
    """Display two events side by side on GET and merge them on POST.

    If no events are supplied via GET params, display event selection form."""

    # field names come from selectable widgets (name_0 for repr, name_1 for pk)
    obj_a_slug = request.GET.get('event_a_0')
    obj_b_slug = request.GET.get('event_b_0')

    if not obj_a_slug and not obj_b_slug:
        context = {
            'title': 'Merge Events',
            'form': EventsSelectionForm(),
            'form_helper': bootstrap_helper_get,
        }
        return render(request, 'workshops/merge_form.html', context)

    obj_a = get_object_or_404(Event, slug=obj_a_slug)
    obj_b = get_object_or_404(Event, slug=obj_b_slug)

    form = EventsMergeForm(initial=dict(event_a=obj_a, event_b=obj_b))

    if request.method == "POST":
        form = EventsMergeForm(request.POST)

        if form.is_valid():
            # merging in process
            data = form.cleaned_data

            obj_a = data['event_a']
            obj_b = data['event_b']

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
                'slug', 'completed', 'assigned_to', 'start', 'end', 'host',
                'administrator', 'url', 'language', 'reg_key', 'admin_fee',
                'invoice_status', 'attendance', 'contact', 'country', 'venue',
                'address', 'latitude', 'longitude', 'learners_pre',
                'learners_post', 'instructors_pre', 'instructors_post',
                'learners_longterm', 'notes',
            )
            # M2M relationships
            difficult = ('tags', 'task_set', 'todoitem_set')

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

    context = {
        'title': 'Merge two events',
        'obj_a': obj_a,
        'obj_b': obj_b,
        'form': form,
    }
    return render(request, 'workshops/events_merge.html', context)


@admin_required
@permission_required('workshops.add_invoicerequest', raise_exception=True)
def event_invoice(request, event_ident):
    try:
        event = Event.get_by_ident(event_ident)
    except ObjectDoesNotExist:
        raise Http404("No event found matching the query.")

    form = InvoiceRequestForm(initial=dict(
        organization=event.host, date=event.start, event=event,
        event_location=event.venue, amount=event.admin_fee,
    ))

    if request.method == 'POST':
        form = InvoiceRequestForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request,
                             'Successfully added an invoice request for {}.'
                             .format(event.get_ident()))
            return redirect(reverse('event_details',
                                    args=[event.get_ident()]))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title_left': 'Event {}'.format(event.get_ident()),
        'title_right': 'New invoice request',
        'event': event,
        'form': form,
        'form_helper': bootstrap_helper,
    }
    return render(request, 'workshops/event_invoice.html', context)


@admin_required
def events_metadata_changed(request):
    """List events with metadata changed."""
    events = Event.objects.active().filter(metadata_changed=True)

    assigned_to, is_admin = assignment_selection(request)

    if assigned_to == 'me':
        events = events.filter(assigned_to=request.user)

    elif assigned_to == 'noone':
        events = events.filter(assigned_to=None)

    elif assigned_to == 'all':
        # no filtering
        pass

    else:
        # no filtering
        pass

    context = {
        'title': 'Events with metadata changed',
        'events': events,
        'is_admin': is_admin,
        'assigned_to': assigned_to,
    }
    return render(request, 'workshops/events_metadata_changed.html', context)


@admin_required
@permission_required('workshops.change_event', raise_exception=True)
def event_review_metadata_changes(request, event_ident):
    """Review changes made to metadata on event's website."""
    try:
        event = Event.get_by_ident(event_ident)
    except Event.DoesNotExist:
        raise Http404('No event found matching the query.')

    metadata = fetch_event_metadata(event.website_url)
    metadata = parse_metadata_from_event_website(metadata)

    # save serialized metadata in session so in case of acceptance we don't
    # reload them
    cmd = WebsiteUpdatesCommand()
    metadata_serialized = cmd.serialize(metadata)
    request.session['metadata_from_event_website'] = metadata_serialized

    context = {
        'title': 'Review changes for {}'.format(str(event)),
        'metadata': metadata,
        'event': event,
    }
    return render(request, 'workshops/event_review_metadata_changes.html',
                  context)


@admin_required
@permission_required('workshops.change_event', raise_exception=True)
def event_accept_metadata_changes(request, event_ident):
    """Review changes made to metadata on event's website."""
    try:
        event = Event.get_by_ident(event_ident)
    except Event.DoesNotExist:
        raise Http404('No event found matching the query.')

    # load serialized metadata from session
    metadata_serialized = request.session.get('metadata_from_event_website')
    if not metadata_serialized:
        raise Http404('Nothing to update.')
    cmd = WebsiteUpdatesCommand()
    metadata = cmd.deserialize(metadata_serialized)

    # update values
    ALLOWED_METADATA = ('start', 'end', 'country', 'venue', 'address',
                        'latitude', 'longitude', 'contact', 'reg_key')
    for key, value in metadata.items():
        if hasattr(event, key) and key in ALLOWED_METADATA:
            setattr(event, key, value)

    # update instructors and helpers
    instructors = ', '.join(metadata.get('instructors', []))
    helpers = ', '.join(metadata.get('helpers', []))
    event.notes += (
        '\n\n---------\nUPDATE {:%Y-%m-%d}:'
        '\nINSTRUCTORS: {}\n\nHELPERS: {}'
        .format(datetime.date.today(), instructors, helpers)
    )

    # save serialized metadata
    event.repository_metadata = metadata_serialized

    # dismiss notification
    event.metadata_all_changes = ''
    event.metadata_changed = False
    event.save()

    # remove metadata from session
    del request.session['metadata_from_event_website']

    messages.success(request,
                     'Successfully updated {}.'.format(event.get_ident()))

    return redirect(reverse('event_details', args=[event.get_ident()]))


@admin_required
@permission_required('workshops.change_event', raise_exception=True)
def event_dismiss_metadata_changes(request, event_ident):
    """Review changes made to metadata on event's website."""
    try:
        event = Event.get_by_ident(event_ident)
    except Event.DoesNotExist:
        raise Http404('No event found matching the query.')

    # dismiss notification
    event.metadata_all_changes = ''
    event.metadata_changed = False
    event.save()

    # remove metadata from session
    if 'metadata_from_event_website' in request.session:
        del request.session['metadata_from_event_website']

    messages.success(request,
                     'Changes to {} were dismissed.'.format(event.get_ident()))

    return redirect(reverse('event_details', args=[event.get_ident()]))


class AllInvoiceRequests(OnlyForAdminsMixin, FilteredListView):
    context_object_name = 'requests'
    template_name = 'workshops/all_invoicerequests.html'
    filter_class = InvoiceRequestFilter
    queryset = InvoiceRequest.objects.all()

    def get_filter_data(self):
        data = self.request.GET.copy()
        data['status'] = data.get('status', '')
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Invoice requests'
        return context


class InvoiceRequestDetails(OnlyForAdminsMixin, DetailView):
    context_object_name = 'object'
    template_name = 'workshops/invoicerequest.html'
    queryset = InvoiceRequest.objects.all()
    pk_url_kwarg = 'request_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Invoice request #{}'.format(self.get_object().pk)
        return context


class InvoiceRequestUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                           UpdateViewContext):
    permission_required = 'workshops.change_invoicerequest'
    model = InvoiceRequest
    form_class = InvoiceRequestUpdateForm
    pk_url_kwarg = 'request_id'
    template_name = 'workshops/generic_form.html'


# ------------------------------------------------------------

@admin_required
def all_tasks(request):
    '''List all tasks.'''

    filter = TaskFilter(
        request.GET,
        queryset=Task.objects.all().select_related('event', 'person', 'role')
                                   .defer('person__notes', 'event__notes')
    )
    tasks = get_pagination_items(request, filter)
    context = {'title' : 'All Tasks',
               'all_tasks' : tasks,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_tasks.html', context)


@admin_required
def task_details(request, task_id):
    '''List details of a particular task.'''
    task = get_object_or_404(Task, pk=task_id)
    context = {'title' : 'Task {0}'.format(task),
               'task' : task}
    return render(request, 'workshops/task.html', context)


@admin_required
@permission_required('workshops.delete_task', raise_exception=True)
def task_delete(request, task_id, event_ident=None):
    '''Delete a task. This is used on the event edit page'''
    t = get_object_or_404(Task, pk=task_id)
    t.delete()

    messages.success(request, 'Task was deleted successfully.')

    if event_ident:
        return redirect(event_edit, event_ident)
    return redirect(all_tasks)


class TaskCreate(OnlyForAdminsMixin, PermissionRequiredMixin,
                 CreateViewContext):
    permission_required = 'workshops.add_task'
    model = Task
    form_class = TaskFullForm
    template_name = 'workshops/generic_form.html'


class TaskUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                 UpdateViewContext):
    permission_required = 'workshops.change_task'
    model = Task
    form_class = TaskFullForm
    pk_url_kwarg = 'task_id'
    template_name = 'workshops/generic_form.html'

#------------------------------------------------------------


@admin_required
@permission_required('workshops.delete_award', raise_exception=True)
def award_delete(request, award_id, person_id=None):
    """Delete an award. This is used on the person edit page."""
    award = get_object_or_404(Award, pk=award_id)
    badge_name = award.badge.name
    award.delete()

    messages.success(request, 'Award was deleted successfully.',
                     extra_tags='awards')

    if person_id:
        # if a second form of URL, then return back to person edit page
        return redirect(person_edit, person_id)

    return redirect(reverse(badge_details, args=[badge_name]))


#------------------------------------------------------------

@admin_required
def all_badges(request):
    '''List all badges.'''

    badges = Badge.objects.order_by('name').annotate(num_awarded=Count('award'))
    context = {'title' : 'All Badges',
               'all_badges' : badges}
    return render(request, 'workshops/all_badges.html', context)


@admin_required
def badge_details(request, badge_name):
    '''List details of a particular badge, list people who were awarded it.'''

    badge = get_object_or_404(Badge, name=badge_name)

    filter = BadgeAwardsFilter(
        request.GET,
        queryset=badge.award_set.select_related('event', 'person', 'badge')
    )
    awards = get_pagination_items(request, filter)

    context = {'title': 'Badge {0}'.format(badge),
               'badge': badge,
               'awards': awards,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/badge.html', context)


@admin_required
@permission_required('workshops.add_award', raise_exception=True)
def badge_award(request, badge_name):
    """Award a badge to someone (== create a new Award)."""
    badge = get_object_or_404(Badge, name=badge_name)

    initial = {
        'badge': badge,
        'awarded': datetime.date.today()
    }

    if request.method == 'GET':
        form = BadgeAwardForm(initial=initial)
    elif request.method == 'POST':
        form = BadgeAwardForm(request.POST, initial=initial)

        if form.is_valid():
            form.save()
            return redirect(reverse('badge_details', args=[badge.name]))

    context = {
        'title': 'Badge {0}'.format(badge),
        'badge': badge,
        'form': form,
        'form_helper': bootstrap_helper,
    }
    return render(request, 'workshops/generic_form.html', context)


#------------------------------------------------------------

@admin_required
def all_trainings(request):
    '''List all Instructor Trainings.'''

    learner = Role.objects.get(name='learner')
    ttt = Tag.objects.get(name='TTT')

    finished = Award.objects.filter(badge__in=Badge.objects.instructor_badges(), event__tags=ttt) \
        .values('event').annotate(finished=Count('person'))
    finished = {f['event']: f['finished'] for f in finished}

    trainings = Task.objects.filter(role=learner).filter(event__tags=ttt).order_by('event__start') \
        .values('event', 'event__slug').annotate(trainees=Count('person'))
    for t in trainings:
        event_id = t['event']
        t['finished'] = finished.get(event_id, 0)

    trainings = get_pagination_items(request, trainings)
    context = {'title': 'All Instructor Trainings',
               'all_trainings': trainings}
    return render(request, 'workshops/all_trainings.html', context)

#------------------------------------------------------------


@admin_required
def workshop_staff(request):
    '''Search for workshop staff.'''
    instructor_badges = Badge.objects.instructor_badges()
    TTT = Tag.objects.get(name='TTT')
    stalled = Tag.objects.get(name='stalled')

    people = Person.objects.filter(airport__isnull=False) \
                           .select_related('airport') \
                           .prefetch_related('badges', 'lessons')

    trainees = Task.objects.filter(event__tags=TTT) \
                           .filter(role__name='learner') \
                           .filter(person__airport__isnull=False) \
                           .exclude(event__tags=stalled) \
                           .exclude(person__badges__in=instructor_badges) \
                           .values_list('person__pk', flat=True)

    # we need to count number of specific roles users had
    # and if they are SWC/DC instructors
    people = people.annotate(
        num_taught=Count(
            Case(
                When(task__role__name='instructor', then=Value(1)),
                output_field=IntegerField()
            )
        ),
        num_helper=Count(
            Case(
                When(task__role__name='helper', then=Value(1)),
                output_field=IntegerField()
            )
        ),
        num_organizer=Count(
            Case(
                When(task__role__name='organizer', then=Value(1)),
                output_field=IntegerField()
            )
        )
    )

    form = WorkshopStaffForm()

    lessons = list()

    if 'submit' in request.GET:
        form = WorkshopStaffForm(request.GET)
        if form.is_valid():
            data = form.cleaned_data

            if data['lessons']:
                lessons = data['lessons']
                # this has to be in a loop to match a *subset* of lessons,
                # not any lesson within the list (as it would be with
                # `.filter(lessons_in=lessons)`)
                for lesson in lessons:
                    people = people.filter(
                        qualification__lesson=lesson
                    )

            if data['airport']:
                x = data['airport'].latitude
                y = data['airport'].longitude
                # using Euclidean distance just because it's faster and easier
                complex_F = ((F('airport__latitude') - x) ** 2 +
                             (F('airport__longitude') - y) ** 2)
                people = people.annotate(distance=complex_F) \
                               .order_by('distance', 'family')

            if data['latitude'] and data['longitude']:
                x = data['latitude']
                y = data['longitude']
                # using Euclidean distance just because it's faster and easier
                complex_F = ((F('airport__latitude') - x) ** 2 +
                             (F('airport__longitude') - y) ** 2)
                people = people.annotate(distance=complex_F) \
                               .order_by('distance', 'family')

            if data['country']:
                people = people.filter(
                    airport__country__in=data['country']
                ).order_by('family')

            if data['gender']:
                people = people.filter(gender=data['gender'])

            if data['instructor_badges']:
                for badge in data['instructor_badges']:
                    people = people.filter(badges__name=badge)

            # it's faster to count role=helper occurences than to check if user
            # had a role=helper
            if data['was_helper']:
                people = people.filter(num_helper__gte=1)

            if data['was_organizer']:
                people = people.filter(num_organizer__gte=1)

            if data['is_in_progress_trainee']:
                q = Q(task__event__tags=TTT) & ~Q(task__event__tags=stalled)
                people = people.filter(q, task__role__name='learner') \
                               .exclude(badges__in=instructor_badges)

            if data['languages']:
                for language in data['languages']:
                    people = people.filter(languages=language)

    emails = people.filter(may_contact=True).values_list('email', flat=True)
    people = get_pagination_items(request, people)
    context = {
        'title': 'Find Workshop Staff',
        'form': form,
        'persons': people,
        'lessons': lessons,
        'instructor_badges': instructor_badges,
        'trainees': trainees,
        'emails': emails,
    }
    return render(request, 'workshops/workshop_staff.html', context)

#------------------------------------------------------------


@admin_required
def search(request):
    '''Search the database by term.'''

    term, hosts, events, persons, airports = '', None, None, None, None

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            term = form.cleaned_data['term']
            tokens = re.split('\s+', term)
            results = list()

            if form.cleaned_data['in_hosts']:
                hosts = Host.objects.filter(
                    Q(domain__contains=term) |
                    Q(fullname__contains=term) |
                    Q(notes__contains=term)) \
                    .order_by('fullname')
                results += list(hosts)

            if form.cleaned_data['in_events']:
                events = Event.objects.filter(
                    Q(slug__contains=term) |
                    Q(notes__contains=term) |
                    Q(host__domain__contains=term) |
                    Q(host__fullname__contains=term) |
                    Q(url__contains=term) |
                    Q(contact__contains=term) |
                    Q(venue__contains=term) |
                    Q(address__contains=term)
                ).order_by('-slug')
                results += list(events)

            if form.cleaned_data['in_persons']:
                # if user searches for two words, assume they mean a person
                # name
                if len(tokens) == 2:
                    name1, name2 = tokens
                    complex_q = (
                        Q(personal__contains=name1) & Q(family__contains=name2)
                    ) | (
                        Q(personal__contains=name2) & Q(family__contains=name1)
                    ) | Q(email__contains=term) | Q(github__contains=term)
                    persons = Person.objects.filter(complex_q)
                else:
                    persons = Person.objects.filter(
                        Q(personal__contains=term) |
                        Q(family__contains=term) |
                        Q(email__contains=term) |
                        Q(github__contains=term)) \
                        .order_by('family')
                results += list(persons)

            if form.cleaned_data['in_airports']:
                airports = Airport.objects.filter(
                    Q(iata__contains=term) |
                    Q(fullname__contains=term)) \
                    .order_by('iata')
                results += list(airports)

            # only 1 record found? Let's move to it immediately
            if len(results) == 1:
                return redirect(results[0].get_absolute_url())

    # if a GET (or any other method) we'll create a blank form
    else:
        form = SearchForm()

    context = {'title' : 'Search',
               'form': form,
               'form_helper': bootstrap_helper,
               'term' : term,
               'hosts' : hosts,
               'events' : events,
               'persons' : persons,
               'airports' : airports}
    return render(request, 'workshops/search.html', context)

#------------------------------------------------------------

@admin_required
def instructors_by_date(request):
    '''Show who taught between begin_date and end_date.'''

    form = DebriefForm()
    if 'begin_date' in request.GET and 'end_date' in request.GET:
        form = DebriefForm(request.GET)

    if form.is_valid():
        start_date = form.cleaned_data['begin_date']
        end_date = form.cleaned_data['end_date']
        rvs = ReportsViewSet()
        tasks = rvs.instructors_by_time_queryset(start_date, end_date)
        emails = tasks.filter(person__may_contact=True)\
                      .exclude(person__email=None)\
                      .values_list('person__email', flat=True)
    else:
        start_date = None
        end_date = None
        tasks = None
        emails = None

    context = {'title': 'List of instructors by time period',
               'form': form,
               'form_helper': bootstrap_helper_get,
               'all_tasks': tasks,
               'emails': emails,
               'start_date': start_date,
               'end_date': end_date}
    return render(request, 'workshops/instructors_by_date.html', context)

#------------------------------------------------------------

@admin_required
def export_badges(request):
    title = 'Badges'
    json_link = reverse('api:export-badges', kwargs={'format': 'json'})
    yaml_link = reverse('api:export-badges', kwargs={'format': 'yaml'})
    context = {
        'title': title,
        'json_link': json_link,
        'yaml_link': yaml_link,
    }
    return render(request, 'workshops/export.html', context)


@admin_required
def export_instructors(request):
    title = 'Instructor Locations'
    json_link = reverse('api:export-instructors', kwargs={'format': 'json'})
    yaml_link = reverse('api:export-instructors', kwargs={'format': 'yaml'})
    context = {
        'title': title,
        'json_link': json_link,
        'yaml_link': yaml_link,
    }
    return render(request, 'workshops/export.html', context)


@admin_required
def export_members(request):
    title = 'SCF Members'
    json_link = reverse('api:export-members', kwargs={'format': 'json'})
    yaml_link = reverse('api:export-members', kwargs={'format': 'yaml'})
    context = {
        'title': title,
        'json_link': json_link,
        'yaml_link': yaml_link,
    }
    return render(request, 'workshops/export.html', context)

#------------------------------------------------------------

@admin_required
def workshops_over_time(request):
    '''Export JSON of count of workshops vs. time.'''
    context = {
        'api_endpoint': reverse('api:reports-workshops-over-time'),
        'title': 'Workshops over time',
    }
    return render(request, 'workshops/time_series.html', context)


@admin_required
def learners_over_time(request):
    '''Export JSON of count of learners vs. time.'''
    context = {
        'api_endpoint': reverse('api:reports-learners-over-time'),
        'title': 'Learners over time',
    }
    return render(request, 'workshops/time_series.html', context)


@admin_required
def instructors_over_time(request):
    '''Export JSON of count of instructors vs. time.'''
    context = {
        'api_endpoint': reverse('api:reports-instructors-over-time'),
        'title': 'Instructors over time',
    }
    return render(request, 'workshops/time_series.html', context)


@admin_required
def instructor_num_taught(request):
    '''Export JSON of how often instructors have taught.'''
    context = {
        'api_endpoint': reverse('api:reports-instructor-num-taught'),
        'title': 'Frequency of Instruction',
    }
    return render(request, 'workshops/instructor_num_taught.html', context)


@admin_required
def all_activity_over_time(request):
    """Display number of workshops (of differend kinds), instructors and
    learners over some specific period of time."""
    context = {
        'api_endpoint': reverse('api:reports-all-activity-over-time'),
        'title': 'All activity over time',
        'start': datetime.date.today() - datetime.timedelta(days=365),
        'end': datetime.date.today(),
    }
    return render(request, 'workshops/all_activity_over_time.html', context)


@admin_required
def workshop_issues(request):
    '''Display workshops in the database whose records need attention.'''

    events = Event.objects.active().past_events().annotate(
        num_instructors=Count(
            Case(
                When(
                    task__role__name='instructor',
                    then=Value(1)
                ),
                output_field=IntegerField()
            )
        )
    )
    events = events.filter(
        Q(attendance=None) | Q(attendance=0) |
        Q(country=None) |
        Q(venue=None) | Q(venue__exact='') |
        Q(address=None) | Q(address__exact='') |
        Q(latitude=None) | Q(longitude=None) |
        Q(start__gt=F('end')) |
        Q(num_instructors=0)
    )

    assigned_to, is_admin = assignment_selection(request)

    if assigned_to == 'me':
        events = events.filter(assigned_to=request.user)

    elif assigned_to == 'noone':
        events = events.filter(assigned_to=None)

    elif assigned_to == 'all':
        # no filtering
        pass

    else:
        # no filtering
        pass

    for e in events:
        e.missing_attendance_ = (not e.attendance)
        e.missing_location_ = (
            not e.country or not e.venue or not e.address or not e.latitude or
            not e.longitude
        )
        e.bad_dates_ = e.start and e.end and (e.start > e.end)
        e.no_instructors_ = not e.num_instructors

    context = {
        'title': 'Workshops with Issues',
        'events': events,
        'is_admin': is_admin,
        'assigned_to': assigned_to,
    }
    return render(request, 'workshops/workshop_issues.html', context)


@admin_required
def instructor_issues(request):
    '''Display instructors in the database who need attention.'''

    # Everyone who has a badge but needs attention.
    instructor_badges = Badge.objects.instructor_badges()
    instructors = Person.objects.filter(badges__in=instructor_badges) \
                                .filter(airport__isnull=True)

    # Everyone who's been in instructor training but doesn't yet have a badge.
    learner = Role.objects.get(name='learner')
    ttt = Tag.objects.get(name='TTT')
    stalled = Tag.objects.get(name='stalled')
    trainees = Task.objects \
        .filter(event__tags__in=[ttt], role=learner) \
        .exclude(person__badges__in=instructor_badges) \
        .order_by('person__family', 'person__personal', 'event__start') \
        .select_related('person', 'event')

    pending_instructors = trainees.exclude(event__tags=stalled)
    pending_instructors_person_ids = pending_instructors.values_list(
        'person__pk', flat=True,
    )

    stalled_instructors = trainees \
        .filter(event__tags=stalled) \
        .exclude(person__id__in=pending_instructors_person_ids)

    context = {
        'title': 'Instructors with Issues',
        'instructors': instructors,
        'pending': pending_instructors,
        'stalled': stalled_instructors,
    }
    return render(request, 'workshops/instructor_issues.html', context)


#------------------------------------------------------------


@admin_required
def object_changes(request, revision_id):
    revision = get_object_or_404(Revision, pk=revision_id)

    # we assume there's only one version per revision
    current_version = revision.version_set.all()[0]
    obj = current_version.object

    try:
        previous_version = get_for_object(obj) \
                                .filter(pk__lt=current_version.pk)[0]
        obj_prev = previous_version.object
    except IndexError:
        # first revision for an object
        previous_version = current_version
        obj_prev = obj

    context = {
        'object_prev': obj_prev,
        'object': obj,
        'previous_version': previous_version,
        'current_version': current_version,
        'revision': revision,
        'title': str(obj),
        'verbose_name': obj._meta.verbose_name,
        'fields': [
            f for f in obj._meta.get_fields()
            if f.concrete
        ],
    }
    return render(request, 'workshops/object_diff.html', context)

# ------------------------------------------------------------


class SWCEventRequest(LoginNotRequiredMixin, EmailSendMixin, CreateViewContext):
    model = EventRequest
    form_class = SWCEventRequestForm
    page_title = 'Request a Software Carpentry Workshop'
    template_name = 'forms/workshop_swc_request.html'
    success_url = reverse_lazy('swc_workshop_request_confirm')
    email_fail_silently = False
    email_kwargs = {
        'to': settings.REQUEST_NOTIFICATIONS_RECIPIENTS,
        'reply_to': None,
    }

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.page_title
        context['form_helper'] = bootstrap_helper_wider_labels
        return context

    def get_subject(self):
        subject = (
            '[{tag}] New workshop request: {affiliation}, {country}'
        ).format(
            tag=self.object.workshop_type.upper(),
            country=self.object.country.name,
            affiliation=self.object.affiliation,
        )
        return subject

    def get_body(self):
        link = self.object.get_absolute_url()
        link_domain = settings.SITE_URL

        body_txt = get_template(
            'mailing/eventrequest.txt'
        ).render({
            'object': self.object,
            'link': link,
            'link_domain': link_domain,
        })

        body_html = get_template(
            'mailing/eventrequest.html'
        ).render({
            'object': self.object,
            'link': link,
            'link_domain': link_domain,
        })
        return body_txt, body_html

    def form_valid(self, form):
        """Send email to admins if the form is valid."""
        data = form.cleaned_data
        self.email_kwargs['reply_to'] = (data['email'], )
        result = super().form_valid(form)
        return result


class SWCEventRequestConfirm(LoginNotRequiredMixin, TemplateView):
    """Display confirmation of received workshop request."""
    template_name = 'forms/workshop_swc_request_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thank you for requesting a workshop'
        return context


class DCEventRequest(SWCEventRequest):
    form_class = DCEventRequestForm
    page_title = 'Request a Data Carpentry Workshop'
    template_name = 'forms/workshop_dc_request.html'
    success_url = reverse_lazy('dc_workshop_request_confirm')


class DCEventRequestConfirm(SWCEventRequestConfirm):
    """Display confirmation of received workshop request."""
    template_name = 'forms/workshop_dc_request_confirm.html'


@admin_required
def all_eventrequests(request):
    """List all event requests."""

    # Set initial value for the "active" radio select.  That's a hack, nothing
    # else worked...
    data = request.GET.copy()  # request.GET is immutable
    data['active'] = data.get('active', 'true')
    data['workshop_type'] = data.get('workshop_type', '')
    filter = EventRequestFilter(
        data,
        queryset=EventRequest.objects.all(),
    )
    eventrequests = get_pagination_items(request, filter)
    context = {
        'title': 'Workshop requests',
        'requests': eventrequests,
        'filter': filter,
        'form_helper': bootstrap_helper_filter,
    }
    return render(request, 'workshops/all_eventrequests.html', context)


class EventRequestDetails(OnlyForAdminsMixin, DetailView):
    queryset = EventRequest.objects.all()
    context_object_name = 'object'
    template_name = 'workshops/eventrequest.html'
    pk_url_kwarg = 'request_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Workshop request #{}'.format(self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(
                initial={'person': self.object.assigned_to}
            )

        person_lookup_helper = BootstrapHelper()
        person_lookup_helper.form_action = reverse('eventrequest_assign',
                                                   args=[self.object.pk])

        context['person_lookup_form'] = person_lookup_form
        context['person_lookup_helper'] = person_lookup_helper
        return context


@admin_required
@permission_required('workshops.change_eventrequest', raise_exception=True)
def eventrequest_discard(request, request_id):
    """Discard EventRequest, ie. set it to inactive."""
    eventrequest = get_object_or_404(EventRequest, active=True, pk=request_id)
    eventrequest.active = False
    eventrequest.save()

    messages.success(request,
                     'Workshop request was discarded successfully.')
    return redirect(reverse('all_eventrequests'))


@admin_required
@permission_required(['workshops.change_eventrequest', 'workshops.add_event'],
                     raise_exception=True)
def eventrequest_accept(request, request_id):
    """Accept event request by creating a new event."""
    eventrequest = get_object_or_404(EventRequest, active=True, pk=request_id)
    form = EventForm()

    if request.method == 'POST':
        form = EventForm(request.POST)

        if form.is_valid():
            event = form.save()
            event.request = eventrequest
            event.save()

            eventrequest.active = False
            eventrequest.save()
            return redirect(reverse('event_details',
                                    args=[event.get_ident()]))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'object': eventrequest,
        'form': form,
    }
    return render(request, 'workshops/eventrequest_accept.html', context)


@admin_required
@permission_required(['workshops.change_eventrequest'], raise_exception=True)
def eventrequest_assign(request, request_id, person_id=None):
    """Set eventrequest.assigned_to. See `assign` docstring for more
    information."""
    event_req = get_object_or_404(EventRequest, pk=request_id)
    assign(request, event_req, person_id)
    return redirect(reverse('eventrequest_details', args=[event_req.pk]))


@login_not_required
def profileupdaterequest_create(request):
    """
    Profile update request form. Accessible to all users (no login required).

    This one is used when instructors want to change their information.
    """
    form = ProfileUpdateRequestForm()
    form_helper = bootstrap_helper_wider_labels
    page_title = 'Update Instructor Profile'

    if request.method == 'POST':
        form = ProfileUpdateRequestForm(request.POST)

        if form.is_valid():
            form.save()

            # TODO: email notification?

            context = {
                'title': 'Thank you for updating your instructor profile',
            }
            return render(request,
                          'forms/profileupdate_confirm.html',
                          context)
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title': page_title,
        'form': form,
        'form_helper': form_helper,
    }
    return render(request, 'forms/profileupdate.html', context)


class AllProfileUpdateRequests(OnlyForAdminsMixin, ListView):
    active_requests = True
    context_object_name = 'requests'
    template_name = 'workshops/all_profileupdaterequests.html'

    def get_queryset(self):
        return ProfileUpdateRequest.objects \
                                   .filter(active=self.active_requests) \
                                   .order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Instructor profile update requests'
        context['active_requests'] = self.active_requests
        return context


class AllClosedProfileUpdateRequests(AllProfileUpdateRequests):
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
                person = Person.objects.get(pk=int(request.GET['person_1']))
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
        airport = Airport.objects.get(iata=update_request.airport_iata)
    except Airport.DoesNotExist:
        airport = None

    context = {
        'title': ('Instructor profile update request #{}'
                  .format(update_request.pk)),
        'new': update_request,
        'old': person,
        'person_form': form,
        'person_selected': person_selected,
        'form_helper': bootstrap_helper_get,
        'airport': airport,
    }
    return render(request, 'workshops/profileupdaterequest.html', context)


class ProfileUpdateRequestFix(OnlyForAdminsMixin, PermissionRequiredMixin,
                              UpdateViewContext):
    permission_required = 'workshops.change_profileupdaterequest'
    model = ProfileUpdateRequest
    form_class = ProfileUpdateRequestFormNoCaptcha
    pk_url_kwarg = 'request_id'
    template_name = 'workshops/generic_form.html'


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
    airport = get_object_or_404(Airport, iata=profileupdate.airport_iata)

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
    person.family = profileupdate.family
    person.email = profileupdate.email
    person.affiliation = profileupdate.affiliation
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

    # we need person to exist in the database in order to set domains and
    # lessons
    if not person.id:
        person.save()

    person.domains = list(profileupdate.domains.all())
    person.languages.set(profileupdate.languages.all())

    # Since Person.lessons uses a intermediate model Qualification, we ought to
    # operate on Qualification objects instead of using Person.lessons as a
    # list.

    # erase old lessons
    Qualification.objects.filter(person=person).delete()
    # add new
    Qualification.objects.bulk_create([
        Qualification(person=person, lesson=L)
        for L in profileupdate.lessons.all()
    ])

    person.save()

    profileupdate.active = False
    profileupdate.save()

    if person_id is None:
        messages.success(request,
                         'New person was added successfully.')
    else:
        messages.success(request,
                         '{} was updated successfully.'.format(person_name))

    return redirect(person.get_absolute_url())


class EventSubmission(LoginNotRequiredMixin, EmailSendMixin, CreateViewContext):
    """Display form for submitting existing workshops."""
    model = EventSubmissionModel
    form_class = EventSubmitForm
    template_name = 'forms/event_submit.html'
    success_url = reverse_lazy('event_submission_confirm')
    email_fail_silently = False
    email_kwargs = {
        'to': settings.REQUEST_NOTIFICATIONS_RECIPIENTS,
    }

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Tell us about your workshop'
        context['form_helper'] = bootstrap_helper_wider_labels
        return context

    def get_subject(self):
        return ('New workshop submission from {}'
                .format(self.object.contact_name))

    def get_body(self):
        link = self.object.get_absolute_url()
        link_domain = settings.SITE_URL
        body_txt = get_template('mailing/event_submission.txt') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        body_html = get_template('mailing/event_submission.html') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        return body_txt, body_html


class EventSubmissionConfirm(LoginNotRequiredMixin, TemplateView):
    """Display confirmation of received workshop submission."""
    template_name = 'forms/event_submission_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thanks for your submission'
        return context


class AllEventSubmissions(OnlyForAdminsMixin, FilteredListView):
    context_object_name = 'submissions'
    template_name = 'workshops/all_eventsubmissions.html'
    filter_class = EventSubmissionFilter
    queryset = EventSubmissionModel.objects.all()

    def get_filter_data(self):
        data = self.request.GET.copy()
        data['active'] = data.get('active', 'true')
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Workshop submissions'
        return context


class EventSubmissionDetails(OnlyForAdminsMixin, DetailView):
    context_object_name = 'object'
    template_name = 'workshops/eventsubmission.html'
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

        person_lookup_helper = BootstrapHelper()
        person_lookup_helper.form_action = reverse('eventsubmission_assign',
                                                   args=[self.object.pk])

        context['person_lookup_form'] = person_lookup_form
        context['person_lookup_helper'] = person_lookup_helper
        return context


class EventSubmissionFix(OnlyForAdminsMixin, PermissionRequiredMixin,
                         UpdateViewContext):
    permission_required = 'workshops.change_eventsubmission'
    model = EventSubmissionModel
    form_class = EventSubmitFormNoCaptcha
    pk_url_kwarg = 'submission_id'
    template_name = 'workshops/generic_form.html'


@admin_required
@permission_required(['workshops.change_eventsubmission',
                      'workshops.add_event'], raise_exception=True)
def eventsubmission_accept(request, submission_id):
    """Accept event submission by creating a new event."""
    submission = get_object_or_404(EventSubmissionModel, active=True,
                                   pk=submission_id)
    form = EventForm()

    if request.method == 'POST':
        form = EventForm(request.POST)

        if form.is_valid():
            event = form.save()

            submission.active = False
            submission.save()
            return redirect(reverse('event_details',
                                    args=[event.get_ident()]))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'object': submission,
        'form': form,
        'title': 'New event',
    }
    return render(request, 'workshops/eventsubmission_accept.html', context)


@admin_required
@permission_required('workshops.change_eventsubmission', raise_exception=True)
def eventsubmission_discard(request, submission_id):
    """Discard EventSubmission, ie. set it to inactive."""
    submission = get_object_or_404(EventSubmissionModel, active=True,
                                   pk=submission_id)
    submission.active = False
    submission.save()

    messages.success(request,
                     'Workshop submission was discarded successfully.')
    return redirect(reverse('all_eventsubmissions'))


@admin_required
@permission_required(['workshops.change_eventrequest'], raise_exception=True)
def eventsubmission_assign(request, submission_id, person_id=None):
    """Set eventsubmission.assigned_to. See `assign` docstring for more
    information."""
    submission = get_object_or_404(EventSubmissionModel, pk=submission_id)
    assign(request, submission, person_id)
    return redirect(submission.get_absolute_url())


class DCSelfOrganizedEventRequest(LoginNotRequiredMixin, EmailSendMixin,
                                  CreateViewContext):
    "Display form for requesting self-organized workshops for Data Carpentry."
    model = DCSelfOrganizedEventRequestModel
    form_class = DCSelfOrganizedEventRequestForm
    # we're reusing DC templates for normal workshop requests
    template_name = 'forms/workshop_dc_request.html'
    success_url = reverse_lazy('dc_workshop_selforganized_request_confirm')
    email_fail_silently = False
    email_kwargs = {
        'to': settings.REQUEST_NOTIFICATIONS_RECIPIENTS,
    }

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Request a self-organized Data Carpentry workshop'
        context['form_helper'] = bootstrap_helper_wider_labels
        return context

    def get_subject(self):
        return ('DC: new self-organized workshop request from {} @ {}'
                .format(self.object.name, self.object.organization))

    def get_body(self):
        link = self.object.get_absolute_url()
        link_domain = settings.SITE_URL
        body_txt = get_template('mailing/dc_self_organized.txt') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        body_html = get_template('mailing/dc_self_organized.html') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        return body_txt, body_html


class DCSelfOrganizedEventRequestConfirm(LoginNotRequiredMixin, TemplateView):
    """Display confirmation of a received self-organized workshop request."""
    # we're reusing DC templates for normal workshop requests
    template_name = 'forms/workshop_dc_request_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thanks for your submission'
        return context


class AllDCSelfOrganizedEventRequests(OnlyForAdminsMixin, FilteredListView):
    context_object_name = 'requests'
    template_name = 'workshops/all_dcselforganizedeventrequests.html'
    filter_class = DCSelfOrganizedEventRequestFilter
    queryset = DCSelfOrganizedEventRequestModel.objects.all()

    def get_filter_data(self):
        data = self.request.GET.copy()
        data['active'] = data.get('active', 'true')
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Data Carpentry self-organized workshop requests'
        return context


class DCSelfOrganizedEventRequestDetails(OnlyForAdminsMixin, DetailView):
    context_object_name = 'object'
    template_name = 'workshops/dcselforganizedeventrequest.html'
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

        person_lookup_helper = BootstrapHelper()
        person_lookup_helper.form_action = reverse(
            'dcselforganizedeventrequest_assign', args=[self.object.pk])

        context['person_lookup_form'] = person_lookup_form
        context['person_lookup_helper'] = person_lookup_helper
        return context


class DCSelfOrganizedEventRequestChange(OnlyForAdminsMixin,
                                        PermissionRequiredMixin,
                                        UpdateViewContext):
    permission_required = 'workshops.change_dcselforganizedeventrequest'
    model = DCSelfOrganizedEventRequestModel
    form_class = DCSelfOrganizedEventRequestFormNoCaptcha
    pk_url_kwarg = 'request_id'
    template_name = 'workshops/generic_form.html'


@admin_required
@permission_required(['workshops.change_dcselforganizedeventrequest'],
                     raise_exception=True)
def dcselforganizedeventrequest_assign(request, request_id, person_id=None):
    """Set eventrequest.assigned_to. See `assign` docstring for more
    information."""
    event_req = get_object_or_404(DCSelfOrganizedEventRequestModel,
                                  pk=request_id)
    assign(request, event_req, person_id)
    return redirect(reverse('dcselforganizedeventrequest_details',
                            args=[event_req.pk]))

#------------------------------------------------------------


@admin_required
@permission_required('workshops.add_todoitem', raise_exception=True)
def todos_add(request, event_ident):
    """Add a standard TodoItems for a specific event."""
    try:
        event = Event.get_by_ident(event_ident)
    except Event.DoesNotExist:
        raise Http404('Event matching query does not exist.')

    dt = datetime.datetime
    timedelta = datetime.timedelta

    initial = []
    base = dt.now()

    if not event.start or not event.end:
        initial = [
            {
                'title': 'Set date with host',
                'due': dt.now() + timedelta(days=30),
                'event': event,
            },
        ]

    formset = TodoFormSet(queryset=TodoItem.objects.none(), initial=initial + [
        {
            'title': 'Set up a workshop website',
            'due': base + timedelta(days=7),
            'event': event,
        },
        {
            'title': 'Find instructor #1',
            'due': base + timedelta(days=14),
            'event': event,
        },
        {
            'title': 'Find instructor #2',
            'due': base + timedelta(days=14),
            'event': event,
        },
        {
            'title': 'Follow up that instructors have booked travel',
            'due': base + timedelta(days=21),
            'event': event,
        },
        {
            'title': 'Set up pre-workshop survey',
            'due': event.start - timedelta(days=7) if event.start else '',
            'event': event,
        },
        {
            'title': 'Make sure instructors are set with materials',
            'due': event.start - timedelta(days=1) if event.start else '',
            'event': event,
        },
        {
            'title': 'Submit invoice',
            'due': event.end + timedelta(days=2) if event.end else '',
            'event': event,
        },
        {
            'title': 'Make sure instructors are reimbursed',
            'due': event.end + timedelta(days=7) if event.end else '',
            'event': event,
        },
        {
            'title': 'Get attendee list',
            'due': event.end + timedelta(days=7) if event.end else '',
            'event': event,
        },
    ])

    if request.method == 'POST':
        formset = TodoFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Successfully added a bunch of TODOs.',
                             extra_tags='todos')
            return redirect(reverse(event_details, args=(event.get_ident(), )))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title': 'Add standard TODOs to the event',
        'formset': formset,
        'helper': bootstrap_helper_inline_formsets,
        'event': event,
    }
    return render(request, 'workshops/todos_add.html', context)


@admin_required
@permission_required('workshops.change_todoitem', raise_exception=True)
def todo_mark_completed(request, todo_id):
    todo = get_object_or_404(TodoItem, pk=todo_id)

    todo.completed = True
    todo.save()

    return HttpResponse()


@admin_required
@permission_required('workshops.change_todoitem', raise_exception=True)
def todo_mark_incompleted(request, todo_id):
    todo = get_object_or_404(TodoItem, pk=todo_id)

    todo.completed = False
    todo.save()

    return HttpResponse()


class TodoItemUpdate(OnlyForAdminsMixin, PermissionRequiredMixin,
                     UpdateViewContext):
    permission_required = 'workshops.change_todoitem'
    model = TodoItem
    form_class = SimpleTodoForm
    pk_url_kwarg = 'todo_id'
    template_name = 'workshops/generic_form.html'

    def get_success_url(self):
        return reverse('event_details', args=[self.object.event.get_ident()])

    def form_valid(self, form):
        """Overwrite default way of showing the success message, because we
        need to add extra tags to it)."""
        self.object = form.save()

        # Important: we need to use ModelFormMixin.form_valid() here!
        # But by doing so we omit SuccessMessageMixin completely, so we need to
        # simulate it.  The code below is almost identical to
        # SuccessMessageMixin.form_valid().
        response = super(ModelFormMixin, self).form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message, extra_tags='todos')
        return response


@admin_required
@permission_required('workshops.delete_todoitem', raise_exception=True)
def todo_delete(request, todo_id):
    """Delete a TodoItem. This is used on the event details page."""
    todo = get_object_or_404(TodoItem, pk=todo_id)
    event_ident = todo.event.get_ident()
    todo.delete()

    messages.success(request, 'TODO was deleted successfully.',
                     extra_tags='todos')

    return redirect(event_details, event_ident)


# ------------------------------------------------------------

@admin_required
def duplicates(request):
    """Find possible duplicates amongst persons.

    Criteria for persons:
    * switched personal/family names
    * same name on different people."""
    names_normal = set(Person.objects.all().values_list('personal', 'family'))
    names_switched = set(Person.objects.all().values_list('family',
                                                          'personal'))
    names = names_normal & names_switched  # intersection

    switched_criteria = Q(id=0)
    # empty query results if names is empty
    for personal, family in names:
        # get people who appear in `names`
        switched_criteria |= (Q(personal=personal) & Q(family=family))

    switched_persons = Person.objects.filter(switched_criteria) \
                                     .order_by('email')

    duplicate_names = Person.objects.values('personal', 'family') \
                                    .order_by() \
                                    .annotate(count_id=Count('id')) \
                                    .filter(count_id__gt=1)

    duplicate_criteria = Q(id=0)
    for name in duplicate_names:
        # get people who appear in `names`
        duplicate_criteria |= (Q(personal=name['personal']) &
                               Q(family=name['family']))
    duplicate_persons = Person.objects.filter(duplicate_criteria) \
                                      .order_by('family', 'personal', 'email')

    context = {
        'title': 'Possible duplicates',
        'switched_persons': switched_persons,
        'duplicate_persons': duplicate_persons,
    }

    return render(request, 'workshops/duplicates.html', context)


@login_not_required
def trainingrequest_create(request):
    """ A form to let all users (no login required) to request Instructor Training. """

    form = TrainingRequestForm()
    page_title = 'Apply for Instructor Training'

    if request.method == 'POST':
        form = TrainingRequestForm(request.POST)

        if form.is_valid():
            form.save()

            # TODO: email notification?

            context = {
                'title': 'Thank you for an instructor training.',
            }
            return render(request,
                          'forms/trainingrequest_confirm.html',
                          context)
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title': page_title,
        'form': form,
        'form_helper': BootstrapHelperWiderLabels(form),
    }
    return render(request, 'forms/trainingrequest.html', context)


class TrainingRequestListView(OnlyForAdminsMixin, ListView):
    context_object_name = 'requests'
    template_name = 'workshops/all_trainingrequests.html'
    queryset = TrainingRequest.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'All training requests'
        return context


class TrainingRequestDetails(OnlyForAdminsMixin, DetailView):
    context_object_name = 'req'
    template_name = 'workshops/trainingrequest.html'
    pk_url_kwarg = 'request_id'
    queryset = TrainingRequest.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Training request #{}'.format(self.get_object().pk)
        return context

# ------------------------------------------------------------
# Views for trainees

@login_required
def trainee_dashboard(request):
    context = {
        'title': 'Your profile',
        'user': request.user,
    }
    return render(request, 'workshops/trainee_dashboard.html', context)


@login_required
def autoupdate_profile(request):
    person = request.user
    form = AutoUpdateProfileForm(instance=person)

    if request.method == 'POST':
        form = AutoUpdateProfileForm(request.POST, instance=person)

        if form.is_valid() and form.instance == person:
            # save lessons
            person.lessons.clear()
            for lesson in form.cleaned_data['lessons']:
                q = Qualification(lesson=lesson, person=person)
                q.save()

            # don't save related lessons
            del form.cleaned_data['lessons']

            person = form.save()

            return redirect(reverse('trainee-dashboard'))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title': 'Update Your Profile',
        'form': form,
        'form_helper': bootstrap_helper,
    }
    return render(request, 'workshops/generic_form_nonav.html', context)
