import csv
import datetime
import io
import re
import requests

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.conf import settings
from django.http import Http404, HttpResponse
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum, Q, Model, ProtectedError
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic.base import ContextMixin
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.decorators import login_required


from workshops.models import \
    Airport, \
    Award, \
    Badge, \
    Event, \
    Lesson, \
    Person, \
    Role, \
    Site, \
    Task
from workshops.check import check_file
from workshops.forms import (
    SearchForm, DebriefForm, InstructorsForm, PersonForm, PersonBulkAddForm,
    EventForm, TaskForm, TaskFullForm, bootstrap_helper,
    bootstrap_helper_with_add, BadgeAwardForm, PersonAwardForm,
    PersonPermissionsForm, bootstrap_helper_filter
)
from workshops.util import (
    earth_distance, upload_person_task_csv,  verify_upload_person_task,
    create_uploaded_persons_tasks, InternalError
)

from workshops.filters import (
    EventFilter, SiteFilter, PersonFilter, TaskFilter, AirportFilter
)

#------------------------------------------------------------

ITEMS_PER_PAGE = 25

#------------------------------------------------------------


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



class LoginRequiredMixin(object):
    """
    Define @login_required-based mixin for class-based views that should allow
    only logged-in users.

    Based on Django docs:
    https://docs.djangoproject.com/en/1.8/topics/class-based-views/intro/#mixins-that-wrap-as-view
    """

    @classmethod
    def as_view(cls, **kwargs):
        view = super(LoginRequiredMixin, cls).as_view(**kwargs)
        return login_required(view)

#------------------------------------------------------------


@login_required
def index(request):
    '''Home page.'''
    upcoming_events = Event.objects.upcoming_events()
    unpublished_events = Event.objects.unpublished_events()
    uninvoiced_events = Event.objects.uninvoiced_events()
    context = {'title': None,
               'upcoming_events': upcoming_events,
               'uninvoiced_events': uninvoiced_events,
               'unpublished_events': unpublished_events}
    return render(request, 'workshops/index.html', context)

#------------------------------------------------------------

SITE_FIELDS = ['domain', 'fullname', 'country', 'notes']


@login_required
def all_sites(request):
    '''List all sites.'''

    filter = SiteFilter(request.GET, queryset=Site.objects.all())
    sites = _get_pagination_items(request, filter)
    context = {'title' : 'All Sites',
               'all_sites' : sites,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_sites.html', context)


@login_required
def site_details(request, site_domain):
    '''List details of a particular site.'''
    site = Site.objects.get(domain=site_domain)
    events = Event.objects.filter(site=site)
    context = {'title' : 'Site {0}'.format(site),
               'site' : site,
               'events' : events}
    return render(request, 'workshops/site.html', context)


class SiteCreate(LoginRequiredMixin, CreateViewContext):
    model = Site
    fields = SITE_FIELDS
    template_name = 'workshops/generic_form.html'


class SiteUpdate(LoginRequiredMixin, UpdateViewContext):
    model = Site
    fields = SITE_FIELDS
    slug_field = 'domain'
    slug_url_kwarg = 'site_domain'
    template_name = 'workshops/generic_form.html'


@login_required
def site_delete(request, site_domain):
    """Delete specific site."""
    try:
        site = get_object_or_404(Site, domain=site_domain)
        site.delete()
        messages.success(request, 'Site was deleted successfully.')
        return redirect(reverse('all_sites'))
    except ProtectedError:
        return _failed_to_delete(request, site)


#------------------------------------------------------------

AIRPORT_FIELDS = ['iata', 'fullname', 'country', 'latitude', 'longitude']


@login_required
def all_airports(request):
    '''List all airports.'''
    filter = AirportFilter(request.GET, queryset=Airport.objects.all())
    airports = _get_pagination_items(request, filter)
    context = {'title' : 'All Airports',
               'all_airports' : airports,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_airports.html', context)


@login_required
def airport_details(request, airport_iata):
    '''List details of a particular airport.'''
    airport = Airport.objects.get(iata=airport_iata)
    context = {'title' : 'Airport {0}'.format(airport),
               'airport' : airport}
    return render(request, 'workshops/airport.html', context)


class AirportCreate(LoginRequiredMixin, CreateViewContext):
    model = Airport
    fields = AIRPORT_FIELDS
    template_name = 'workshops/generic_form.html'


class AirportUpdate(LoginRequiredMixin, UpdateViewContext):
    model = Airport
    fields = AIRPORT_FIELDS
    slug_field = 'iata'
    slug_url_kwarg = 'airport_iata'
    template_name = 'workshops/generic_form.html'


@login_required
def airport_delete(request, airport_iata):
    """Delete specific airport."""
    try:
        airport = get_object_or_404(Airport, iata=airport_iata)
        airport.delete()
        messages.success(request, 'Airport was deleted successfully.')
        return redirect(reverse('all_airports'))
    except ProtectedError:
        return _failed_to_delete(request, airport)

#------------------------------------------------------------


@login_required
def all_persons(request):
    '''List all persons.'''

    filter = PersonFilter(
        request.GET,
        queryset=Person.objects.all().defer('notes')  # notes are too large
                                     .prefetch_related('badges')
    )
    persons = _get_pagination_items(request, filter)
    instructor = Badge.objects.get(name='instructor')
    context = {'title' : 'All Persons',
               'all_persons' : persons,
               'instructor': instructor,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_persons.html', context)


@login_required
def person_details(request, person_id):
    '''List details of a particular person.'''
    person = Person.objects.get(id=person_id)
    awards = Award.objects.filter(person__id=person_id)
    tasks = Task.objects.filter(person__id=person_id)
    context = {'title' : 'Person {0}'.format(person),
               'person' : person,
               'awards' : awards,
               'tasks' : tasks}
    return render(request, 'workshops/person.html', context)


@login_required
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


@login_required
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


@login_required
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
        middles = request.POST.getlist("middle")
        families = request.POST.getlist("family")
        emails = request.POST.getlist("email")
        events = request.POST.getlist("event")
        roles = request.POST.getlist("role")
        data_update = zip(personals, middles, families, emails, events, roles)
        for k, record in enumerate(data_update):
            personal, middle, family, email, event, role = record
            # "field or None" converts empty strings to None values
            persons_tasks[k] = {
                'personal': personal,
                'middle': middle or None,
                'family': family,
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
                       'persons_tasks': persons_tasks}
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
                verify_upload_person_task(persons_tasks)
                context = {'title': 'Confirm uploaded data',
                           'persons_tasks': persons_tasks}
                return render(request,
                              'workshops/person_bulk_add_results.html',
                              context, status=400)

            else:
                request.session['bulk-add-people'] = None
                messages.add_message(request, messages.SUCCESS,
                                     "Successfully uploaded {0} persons and {1} tasks."
                                     .format(len(persons_created), len(tasks_created)))
                return redirect('person_bulk_add')

        else:
            # any "cancel" or no "confirm" in POST cancels the upload
            request.session['bulk-add-people'] = None
            return redirect('person_bulk_add')

    else:
        # alters persons_tasks via reference
        verify_upload_person_task(persons_tasks)

        context = {'title': 'Confirm uploaded data',
                   'persons_tasks': persons_tasks}
        return render(request, 'workshops/person_bulk_add_results.html',
                      context)


class PersonCreate(LoginRequiredMixin, CreateViewContext):
    model = Person
    form_class = PersonForm
    template_name = 'workshops/generic_form.html'


@login_required
def person_edit(request, person_id):
    try:
        person = Person.objects.get(pk=person_id)
        awards = person.award_set.order_by('badge__name')
    except ObjectDoesNotExist:
        raise Http404("No person found matching the query.")

    person_form = PersonForm(prefix='person', instance=person)
    award_form = PersonAwardForm(prefix='award', initial={
        'awarded': datetime.date.today(),
        'person': person,
    })

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
                )

                # to reset the form values
                return redirect(request.path)

            else:
                messages.error(request, 'Fix errors below.')

        else:
            person_form = PersonForm(request.POST, prefix='person',
                                     instance=person)
            if person_form.is_valid():
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
               'form_helper': bootstrap_helper,
               'form_helper_with_add': bootstrap_helper_with_add,
               }
    return render(request, 'workshops/person_edit_form.html', context)


@login_required
def person_delete(request, person_id):
    """Delete specific person."""
    try:
        person = get_object_or_404(Person, pk=person_id)
        person.delete()

        messages.success(request, 'Person was deleted successfully.')
        return redirect(reverse('all_persons'))
    except ProtectedError:
        return _failed_to_delete(request, person)


class PersonPermissions(LoginRequiredMixin, UpdateViewContext):
    model = Person
    form_class = PersonPermissionsForm
    pk_url_kwarg = 'person_id'
    template_name = 'workshops/generic_form.html'


@login_required
def person_password(request, person_id):
    user = get_object_or_404(Person, pk=person_id)

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


#------------------------------------------------------------

@login_required
def all_events(request):
    '''List all events.'''
    filter = EventFilter(
        request.GET,
        queryset=Event.objects.all().defer('notes')  # notes are too large
                                    .prefetch_related('site', 'tags'),
    )
    events = _get_pagination_items(request, filter)
    context = {'title' : 'All Events',
               'all_events' : events,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_events.html', context)


@login_required
def event_details(request, event_ident):
    '''List details of a particular event.'''

    event = Event.get_by_ident(event_ident)
    tasks = Task.objects.filter(event__id=event.id).order_by('role__name')
    context = {'title' : 'Event {0}'.format(event),
               'event' : event,
               'tasks' : tasks}
    return render(request, 'workshops/event.html', context)


@login_required
def validate_event(request, event_ident):
    '''Check the event's home page *or* the specified URL (for testing).'''
    page_url, error_messages = None, []
    event = Event.get_by_ident(event_ident)
    github_url = request.GET.get('url', None) # for manual override
    if github_url is None:
        github_url = event.url
    if github_url is not None:
        page_url = github_url.replace('github.com', 'raw.githubusercontent.com').rstrip('/') + '/gh-pages/index.html'

        try:
            response = requests.get(page_url)

            if response.status_code != 200:
                error_messages.append('Request for {0} returned status code {1}'.format(page_url, response.status_code))
            else:
                error_messages = check_file(page_url, response.text)
        except requests.ConnectionError:
            error_messages = ["Network connection error.", ]
    context = {'title' : 'Validate Event {0}'.format(event),
               'event' : event,
               'page' : page_url,
               'error_messages' : error_messages}
    return render(request, 'workshops/validate_event.html', context)


class EventCreate(LoginRequiredMixin, CreateViewContext):
    model = Event
    form_class = EventForm
    template_name = 'workshops/generic_form.html'


@login_required
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


@login_required
def event_delete(request, event_ident):
    """Delete event, its tasks and related awards."""
    try:
        event = Event.get_by_ident(event_ident)
    except ObjectDoesNotExist:
        raise Http404("No event found matching the query.")

    event.delete()

    messages.success(request,
                     'Event, its tasks and related awards were deleted '
                     'successfully.')
    return redirect(reverse('all_events'))

#------------------------------------------------------------

@login_required
def all_tasks(request):
    '''List all tasks.'''

    filter = TaskFilter(
        request.GET,
        queryset=Task.objects.all().select_related('event', 'person', 'role')
                                   .defer('person__notes', 'event__notes')
    )
    tasks = _get_pagination_items(request, filter)
    context = {'title' : 'All Tasks',
               'all_tasks' : tasks,
               'filter': filter,
               'form_helper': bootstrap_helper_filter}
    return render(request, 'workshops/all_tasks.html', context)


@login_required
def task_details(request, task_id):
    '''List details of a particular task.'''
    task = Task.objects.get(pk=task_id)
    context = {'title' : 'Task {0}'.format(task),
               'task' : task}
    return render(request, 'workshops/task.html', context)


@login_required
def task_delete(request, task_id):
    '''Delete a task. This is used on the event edit page'''
    t = get_object_or_404(Task, pk=task_id)
    t.delete()

    messages.success(request, 'Task was deleted successfully.')
    return redirect(event_edit, t.event.id)


class TaskCreate(LoginRequiredMixin, CreateViewContext):
    model = Task
    form_class = TaskFullForm
    template_name = 'workshops/generic_form.html'


class TaskUpdate(LoginRequiredMixin, UpdateViewContext):
    model = Task
    form_class = TaskFullForm
    pk_url_kwarg = 'task_id'
    template_name = 'workshops/generic_form.html'


#------------------------------------------------------------

@login_required
def all_badges(request):
    '''List all badges.'''

    badges = Badge.objects.order_by('name').annotate(num_awarded=Count('award'))
    context = {'title' : 'All Badges',
               'all_badges' : badges}
    return render(request, 'workshops/all_badges.html', context)


@login_required
def badge_details(request, badge_name):
    '''List details of a particular event.'''

    badge = Badge.objects.get(name=badge_name)

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

    awards = badge.award_set.all()
    awards = _get_pagination_items(request, awards)

    context = {'title': 'Badge {0}'.format(badge),
               'badge': badge,
               'awards': awards,
               'form': form,
               'form_helper': bootstrap_helper}
    return render(request, 'workshops/badge.html', context)


#------------------------------------------------------------


@login_required
def instructors(request):
    '''Search for instructors.'''

    persons = None

    if request.method == 'POST':
        form = InstructorsForm(request.POST)
        if form.is_valid():

            # Filter by qualifications.
            persons = Person.objects.filter(airport__isnull=False)
            for les in Lesson.objects.all():
                if form.cleaned_data[les.name]:
                    persons = persons.filter(qualification__lesson=les)

            # Add metadata which we will eventually filter by
            for p in persons:
                p.num_taught = p.task_set.instructors().count()

            # Sort by location.
            loc = (form.cleaned_data['latitude'],
                   form.cleaned_data['longitude'])
            persons = [(earth_distance(loc, (p.airport.latitude, p.airport.longitude)), p)
                       for p in persons]
            persons.sort(
                key=lambda distance_person: (
                    distance_person[0],
                    distance_person[1].family,
                    distance_person[1].personal,
                    distance_person[1].middle))

            # Return number desired.
            wanted = form.cleaned_data['wanted']
            persons = [x[1] for x in persons[:wanted]]

    # if a GET (or any other method) we'll create a blank form
    else:
        form = InstructorsForm()

    context = {'title' : 'Find Instructors',
               'form': form,
               'persons' : persons}
    return render(request, 'workshops/instructors.html', context)

#------------------------------------------------------------


@login_required
def search(request):
    '''Search the database by term.'''

    term, sites, events, persons, airports = '', None, None, None, None

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            term = form.cleaned_data['term']
            if form.cleaned_data['in_sites']:
                sites = Site.objects.filter(
                    Q(domain__contains=term) |
                    Q(fullname__contains=term) |
                    Q(notes__contains=term)) \
                    .order_by('fullname')
            if form.cleaned_data['in_events']:
                events = Event.objects.filter(
                    Q(slug__contains=term) |
                    Q(notes__contains=term) |
                    Q(site__domain__contains=term) |
                    Q(site__fullname__contains=term)) \
                    .order_by('-slug')
            if form.cleaned_data['in_persons']:
                persons = Person.objects.filter(
                    Q(personal__contains=term) |
                    Q(family__contains=term) |
                    Q(email__contains=term) |
                    Q(github__contains=term)) \
                    .order_by('family')
            if form.cleaned_data['in_airports']:
                airports = Airport.objects.filter(
                    Q(iata__contains=term) |
                    Q(fullname__contains=term)) \
                    .order_by('iata')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = SearchForm()

    context = {'title' : 'Search',
               'form': form,
               'form_helper': bootstrap_helper,
               'term' : term,
               'sites' : sites,
               'events' : events,
               'persons' : persons,
               'airports' : airports}
    return render(request, 'workshops/search.html', context)

#------------------------------------------------------------

@login_required
def debrief(request):
    '''Show who taught between begin_date and end_date.'''

    tasks = None

    start_date = end_date = None

    if request.method == 'POST':
        form = DebriefForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['begin_date']
            end_date = form.cleaned_data['end_date']
            tasks = Task.objects.filter(
                event__start__gte=start_date,
                event__end__lte=end_date,
                role__name='instructor',
                person__may_contact=True,
            ).order_by('event', 'person', 'role')

    else:
        # if a GET (or any other method) we'll create a blank form
        form = DebriefForm()

    context = {'title': 'Debrief',
               'form': form,
               'form_helper': bootstrap_helper,
               'all_tasks': tasks,
               'start_date': start_date,
               'end_date': end_date}
    return render(request, 'workshops/debrief.html', context)

#------------------------------------------------------------

def _export_badges():
    '''Collect badge data as YAML.'''
    result = {}
    for badge in Badge.objects.all():
        persons = Person.objects.filter(award__badge_id=badge.id)
        result[badge.name] = [
            {"user": p.username, "name": p.get_full_name()} for p in persons
        ]
    return result


def _export_instructors():
    '''Collect instructor airport locations as YAML.'''

    # Get all the people associated with an airport.
    def _get_people(airport):
        return [[p.username, p.get_full_name()]
                for p in airport.person_set.all()]

    # Exclude airports with no instructors, then create a list of dicts.
    airports = Airport.objects.exclude(person=None)
    return [{'airport' : str(a.fullname),
             'latlng' : '{0},{1}'.format(a.latitude, a.longitude),
             'who'  : _get_people(a)}
            for a in airports]


@login_required
def export(request, name):
    '''Export data as YAML for inclusion in main web site.'''
    data = None
    if name == 'badges':
        title, data = 'Badges', _export_badges()
    elif name == 'instructors':
        title, data = 'Instructor Locations', _export_instructors()
    else:
        title, data = 'Error', None # FIXME - need an error message
    context = {'title' : title,
               'data' : data}
    return render(request, 'workshops/export.html', context)

#------------------------------------------------------------

@login_required
def workshops_over_time(request):
    '''Export CSV of count of workshops vs. time.'''

    data = dict(Event.objects
                     .past_events()
                     .values_list('start')
                     .annotate(Count('id')))
    return _time_series(request, data, 'Workshop over time')


@login_required
def learners_over_time(request):
    '''Export CSV of count of learners vs. time.'''

    data = dict(Event.objects
                     .past_events()
                     .values_list('start')
                     .annotate(Sum('attendance')))
    return _time_series(request, data, 'Learners over time')


@login_required
def instructors_over_time(request):
    '''Export CSV of count of instructors vs. time.'''

    badge = Badge.objects.get(name='instructor')
    data = dict(badge.award_set
                     .values_list('awarded')
                     .annotate(Count('person__id')))
    return _time_series(request, data, 'Instructors over time')


@login_required
def problems(request):
    '''Display problems in the database.'''

    subject = 'attendance figures for '
    body_pre = 'Hi,\nCan you please send us an attendance list (or even just a head count) for the '
    body_post = ' workshop?\nThanks,\nSoftware Carpentry'

    host = Role.objects.get(name='host')
    instructor = Role.objects.get(name='instructor')
    missing_attendance = Event.objects.past_events().\
        filter(Q(attendance=None) | Q(attendance=0))
    for e in missing_attendance:
        tasks = Task.objects.filter(event=e).\
            filter(Q(role=host) | Q(role=instructor))
        e.mailto = [t.person.email for t in tasks if t.person.email]
    context = {'title': 'Problems',
               'missing_attendance': missing_attendance,
               'subject': subject,
               'body_pre': body_pre,
               'body_post': body_post}
    return render(request, 'workshops/problems.html', context)

#------------------------------------------------------------

def _get_pagination_items(request, all_objects):
    '''Select paginated items.'''

    # Get parameters.
    items = request.GET.get('items_per_page', ITEMS_PER_PAGE)
    if items != 'all':
        try:
            items = int(items)
        except ValueError:
            items = ITEMS_PER_PAGE
    else:
        # Show everything.
        items = all_objects.count()

    # Figure out where we are.
    page = request.GET.get('page')

    # Show selected items.
    paginator = Paginator(all_objects, items)

    # Select the sites.
    try:
        result = paginator.page(page)

    # If page is not an integer, deliver first page.
    except PageNotAnInteger:
        result = paginator.page(1)

    # If page is out of range, deliver last page of results.
    except EmptyPage:
        result = paginator.page(paginator.num_pages)

    return result


def _time_series(request, data, title):
    '''Prepare time-series data for display and render it.'''

    # Make sure addition will work.
    for key in data:
        if data[key] is None:
            data[key] = 0

    # Create running total.
    data = list(data.items())
    data.sort()
    for i in range(1, len(data)):
        data[i] = (data[i][0], data[i][1] + data[i-1][1])

    # Textualize and display.
    data = '\n'.join(['{0},{1}'.format(*d) for d in data])
    context = {'title': title,
               'data': data}
    return render(request, 'workshops/time_series.html', context)


def _failed_to_delete(request, object, back=None):
    context = {
        'title': 'Failed to delete',
        'back': back or object.get_absolute_url,
        'object': object,
        'refs': dict(),
    }

    # all reverse FK fields in the object model
    fields = [
        f for f in object._meta.get_fields()
        if (f.one_to_many or f.one_to_one or f.many_to_many) and f.auto_created
    ]
    # find out their real names to access with getattr(object, field_name)
    field_names = [f.related_name or f.name + "_set" for f in fields]

    for field_name in field_names:
        try:
            context['refs'][field_name] = getattr(object, field_name)
        except AttributeError:
            # fail silently if we cannot get some object.field_name
            pass

    return render(request, 'workshops/failed_to_delete.html', context)
