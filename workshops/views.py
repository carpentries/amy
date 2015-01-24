import re
import yaml
import csv
import requests

from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Model
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic.base import ContextMixin
from django.views.generic.edit import CreateView, UpdateView

from workshops.models import \
    Airport, \
    Award, \
    Badge, \
    Event, \
    Person, \
    Role, \
    Site, \
    Skill, \
    Task
from workshops.check import check_file
from workshops.forms import SearchForm, InstructorsForm, PersonBulkAddForm
from workshops.util import earth_distance, upload_person_task_csv, verify_upload_person_task

#------------------------------------------------------------

ITEMS_PER_PAGE = 25

#------------------------------------------------------------


class CreateViewContext(CreateView):
    """
    Class-based view for creating objects that extends default template context
    by adding model class used in objects creation.
    """

    def get_context_data(self, **kwargs):
        context = super(CreateViewContext, self).get_context_data(**kwargs)

        # self.model is available in CreateView as the model class being
        # used to create new model instance
        context['model'] = self.model

        if self.model and issubclass(self.model, Model):
            context['title'] = 'New {}'.format(self.model._meta.verbose_name)
        else:
            context['title'] = 'New object'

        return context


class UpdateViewContext(UpdateView):
    """
    Class-based view for updating objects that extends default template context
    by adding proper page title.
    """

    def get_context_data(self, **kwargs):
        context = super(UpdateViewContext, self).get_context_data(**kwargs)

        # self.model is available in UpdateView as the model class being
        # used to update model instance
        context['model'] = self.model

        # self.object is available in UpdateView as the object being currently
        # edited
        context['title'] = str(self.object)
        return context

#------------------------------------------------------------


def index(request):
    '''Home page.'''
    upcoming_events = Event.objects.upcoming_events()
    unpublished_events = Event.objects.unpublished_events()
    context = {'title' : None,
               'upcoming_events' : upcoming_events,
               'unpublished_events' : unpublished_events}
    return render(request, 'workshops/index.html', context)

#------------------------------------------------------------

SITE_FIELDS = ['domain', 'fullname', 'country', 'notes']


def all_sites(request):
    '''List all sites.'''

    all_sites = Site.objects.order_by('domain')
    sites = _get_pagination_items(request, all_sites)
    user_can_add = request.user.has_perm('edit')
    context = {'title' : 'All Sites',
               'all_sites' : sites,
               'user_can_add' : user_can_add}
    return render(request, 'workshops/all_sites.html', context)


def site_details(request, site_domain):
    '''List details of a particular site.'''
    site = Site.objects.get(domain=site_domain)
    events = Event.objects.filter(site=site)
    context = {'title' : 'Site {0}'.format(site),
               'site' : site,
               'events' : events}
    return render(request, 'workshops/site.html', context)


class SiteCreate(CreateViewContext):
    model = Site
    fields = SITE_FIELDS


class SiteUpdate(UpdateViewContext):
    model = Site
    fields = SITE_FIELDS
    slug_field = 'domain'
    slug_url_kwarg = 'site_domain'

#------------------------------------------------------------

AIRPORT_FIELDS = ['iata', 'fullname', 'country', 'latitude', 'longitude']


def all_airports(request):
    '''List all airports.'''
    all_airports = Airport.objects.order_by('iata')
    user_can_add = request.user.has_perm('edit')
    context = {'title' : 'All Airports',
               'all_airports' : all_airports,
               'user_can_add' : user_can_add}
    return render(request, 'workshops/all_airports.html', context)


def airport_details(request, airport_iata):
    '''List details of a particular airport.'''
    airport = Airport.objects.get(iata=airport_iata)
    context = {'title' : 'Airport {0}'.format(airport),
               'airport' : airport}
    return render(request, 'workshops/airport.html', context)


class AirportCreate(CreateViewContext):
    model = Airport
    fields = AIRPORT_FIELDS


class AirportUpdate(UpdateViewContext):
    model = Airport
    fields = AIRPORT_FIELDS
    slug_field = 'iata'
    slug_url_kwarg = 'airport_iata'

#------------------------------------------------------------

def all_persons(request):
    '''List all persons.'''

    all_persons = Person.objects.order_by('family', 'personal')
    persons = _get_pagination_items(request, all_persons)
    context = {'title' : 'All Persons',
               'all_persons' : persons}
    return render(request, 'workshops/all_persons.html', context)


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


def person_bulk_add(request):
    if request.method == 'POST':
        form = PersonBulkAddForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                persons_tasks = upload_person_task_csv(request.FILES['file'])
            except csv.Error as e:
                messages.add_message(request, messages.ERROR,
                                     "Error processing uploaded .CSV file: {}"
                                     .format(e))
            else:
                # instead of insta-saving, put everything into session
                # then redirect to confirmation page which in turn saves the
                # data
                request.session['bulk-add-people'] = persons_tasks
                return redirect('person_bulk_add_confirmation')

    else:
        form = PersonBulkAddForm()

    context = {'title': 'Bulk Add People',
               'form': form}
    return render(request, 'workshops/person_bulk_add_form.html', context)


def person_bulk_add_confirmation(request):
    """
    This view allows for manipulating and saving session-stored upload data.
    """
    persons_tasks = request.session.get('bulk-add-people')

    # if the session is empty, add message and redirect
    if not persons_tasks:
        messages.warning(request, "Could not locate CSV data, please try the upload again.")
        redirect('person_bulk_add')

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
            persons_tasks[k]['person'] = {
                'personal': personal,
                'middle': middle,
                'family': family,
                'email': email
            }
            if event:
                persons_tasks[k]['event'] = event
            if role:
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

        elif (request.POST.get('confirm', None) and
                not request.POST.get('cancel', None)):
            # there must be "confirm" and no "cancel" in POST in order to save

            try:
                records = 0
                with transaction.atomic():
                    for row in persons_tasks:
                        # create person
                        p = Person(**row['person'])
                        p.save()
                        records += 1

                        # create task if data supplied
                        if row['event'] and row['role']:
                            e = Event.objects.get(slug=row['event'])
                            r = Role.objects.get(name=row['role'])
                            t = Task(person=p, event=e, role=r)
                            t.save()
                            records += 1

            except (IntegrityError, ObjectDoesNotExist) as e:
                messages.add_message(request, messages.ERROR,
                                     "Error saving data to the database: {}. "
                                     "Please make sure to fix all errors "
                                     "listed below.".format(e))
                _verify_upload_person_task(persons_tasks)
                context = {'title': 'Confirm uploaded data',
                           'persons_tasks': persons_tasks}
                return render(request,
                              'workshops/person_bulk_add_results.html',
                              context)

            else:
                request.session['bulk-add-people'] = None
                messages.add_message(request, messages.SUCCESS,
                                     "Successfully bulk-loaded {} records."
                                     .format(records))
                return redirect('person_bulk_add')

        else:
            # any "cancel" or no "confirm" in POST cancels the upload
            request.session['bulk-add-people'] = None
            return redirect('person_bulk_add')

    else:
        # alters persons_tasks via reference
        _verify_upload_person_task(persons_tasks)

        context = {'title': 'Confirm uploaded data',
                   'persons_tasks': persons_tasks}
        return render(request, 'workshops/person_bulk_add_results.html',
                      context)



class PersonCreate(CreateViewContext):
    model = Person
    fields = '__all__'


class PersonUpdate(UpdateViewContext):
    model = Person
    fields = '__all__'
    pk_url_kwarg = 'person_id'


#------------------------------------------------------------

def all_events(request):
    '''List all events.'''

    all_events = Event.objects.all()
    events = _get_pagination_items(request, all_events)
    for e in events:
        e.num_instructors = e.task_set.filter(role__name='instructor').count()
    context = {'title' : 'All Events',
               'all_events' : events}
    return render(request, 'workshops/all_events.html', context)


def event_details(request, event_ident):
    '''List details of a particular event.'''

    event = Event.get_by_ident(event_ident)
    tasks = Task.objects.filter(event__id=event.id).order_by('role__name')
    context = {'title' : 'Event {0}'.format(event),
               'event' : event,
               'tasks' : tasks}
    return render(request, 'workshops/event.html', context)

def validate_event(request, event_ident):
    '''Check the event's home page *or* the specified URL (for testing).'''
    page_url, error_messages = None, []
    event = Event.get_by_ident(event_ident)
    github_url = request.GET.get('url', None) # for manual override
    if github_url is None:
        github_url = event.url
    if github_url is not None:
        page_url = github_url.replace('github.com', 'raw.githubusercontent.com').rstrip('/') + '/gh-pages/index.html'
        response = requests.get(page_url)
        if response.status_code != 200:
            error_messages.append('Request for {0} returned status code {1}'.format(page_url, response.status_code))
        else:
            valid, error_messages = check_file(page_url, response.text)
    context = {'title' : 'Validate Event {0}'.format(event),
               'event' : event,
               'page' : page_url,
               'error_messages' : error_messages}
    return render(request, 'workshops/validate_event.html', context)


class EventCreate(CreateViewContext):
    model = Event
    fields = '__all__'


class EventUpdate(UpdateViewContext):
    model = Event
    fields = '__all__'
    pk_url_kwarg = 'event_ident'

#------------------------------------------------------------

TASK_FIELDS = ['event', 'person', 'role']


def all_tasks(request):
    '''List all tasks.'''

    all_tasks = Task.objects.order_by('event', 'person', 'role')
    tasks = _get_pagination_items(request, all_tasks)
    user_can_add = request.user.has_perm('edit')
    context = {'title' : 'All Tasks',
               'all_tasks' : tasks,
               'user_can_add' : user_can_add}
    return render(request, 'workshops/all_tasks.html', context)


def task_details(request, task_id):
    '''List details of a particular task.'''
    task = Task.objects.get(pk=task_id)
    context = {'title' : 'Task {0}'.format(task),
               'task' : task}
    return render(request, 'workshops/task.html', context)


class TaskCreate(CreateViewContext):
    model = Task
    fields = TASK_FIELDS


class TaskUpdate(UpdateViewContext):
    model = Task
    fields = TASK_FIELDS
    pk_url_kwarg = 'task_id'


#------------------------------------------------------------

def all_badges(request):
    '''List all badges.'''

    all_badges = Badge.objects.order_by('name')
    for b in all_badges:
        b.num_awarded = Award.objects.filter(badge_id=b.id).count()
    context = {'title' : 'All Badges',
               'all_badges' : all_badges}
    return render(request, 'workshops/all_badges.html', context)


def badge_details(request, badge_name):
    '''Show who has a particular badge.'''

    badge = Badge.objects.get(name=badge_name)
    all_awards = Award.objects.filter(badge_id=badge.id)
    awards = _get_pagination_items(request, all_awards)
    context = {'title' : 'Badge {0}'.format(badge.title),
               'badge' : badge,
               'all_awards' : awards}
    return render(request, 'workshops/badge.html', context)

#------------------------------------------------------------

def instructors(request):
    '''Search for instructors.'''

    persons = None

    if request.method == 'POST':
        form = InstructorsForm(request.POST)
        if form.is_valid():

            # Filter by skills.
            persons = Person.objects.filter(airport__isnull=False)
            for s in Skill.objects.all():
                if form.cleaned_data[s.name]:
                    persons = persons.filter(qualification__skill=s)

            # Add metadata which we will eventually filter by
            for p in persons:
                p.num_taught = \
                    p.task_set.filter(role__name='instructor').count()

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

def search(request):
    '''Search the database by term.'''

    term, sites, events, persons = '', None, None, None

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            term = form.cleaned_data['term']
            if form.cleaned_data['in_sites']:
                sites = Site.objects.filter(
                    Q(domain__contains=term) |
                    Q(fullname__contains=term) |
                    Q(notes__contains=term))
            if form.cleaned_data['in_events']:
                events = Event.objects.filter(
                    Q(slug__contains=term) |
                    Q(notes__contains=term))
            if form.cleaned_data['in_persons']:
                persons = Person.objects.filter(
                    Q(personal__contains=term) |
                    Q(family__contains=term) |
                    Q(email__contains=term) |
                    Q(github__contains=term))
        else:
            pass # FIXME: error message

    # if a GET (or any other method) we'll create a blank form
    else:
        form = SearchForm()

    context = {'title' : 'Search',
               'form': form,
               'term' : term,
               'sites' : sites,
               'events' : events,
               'persons' : persons}
    return render(request, 'workshops/search.html', context)

#------------------------------------------------------------

def _export_badges():
    '''Collect badge data as YAML.'''
    result = {}
    for badge in Badge.objects.all():
        persons = Person.objects.filter(award__badge_id=badge.id)
        result[badge.name] = [{"user" : p.slug, "name" : p.fullname()} for p in persons]
    return result


def _export_instructors():
    '''Collect instructor airport locations as YAML.'''
    # Exclude airports with no instructors, and add the number of instructors per airport
    airports = Airport.objects.exclude(person=None).annotate(num_persons=Count('person'))
    return [{'airport' : str(a.fullname),
             'latlng' : '{0},{1}'.format(a.latitude, a.longitude),
             'count'  : a.num_persons}
            for a in airports]


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

def _get_pagination_items(request, all_objects):
    '''Select paginated items.'''

    # Get parameters.
    items = request.GET.get('items_per_page', ITEMS_PER_PAGE)
    if items != 'all':
        try:
            items = int(items)
        except ValueError:
            items = ITEMS_PER_PAGE

    # Figure out where we are.
    page = request.GET.get('page')

    # Show everything.
    if items == 'all':
        result = all_objects

    # Show selected items.
    else:
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
