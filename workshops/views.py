import yaml
import requests

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import CreateView, UpdateView
from django.db.models import Count, Q

from workshops.models import Site, Airport, Event, Person, Task, Cohort, Skill, Trainee, Badge, Award
from workshops.forms import InstructorsForm, SearchForm
from workshops.util import earth_distance
from workshops.check import check_file

#------------------------------------------------------------

ITEMS_PER_PAGE = 25

#------------------------------------------------------------

def index(request):
    '''Home page.'''
    upcoming_events = Event.objects.upcoming_events()
    context = {'title' : None,
               'upcoming_events' : upcoming_events}
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


class SiteCreate(CreateView):
    model = Site
    fields = SITE_FIELDS


class SiteUpdate(UpdateView):
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


class AirportCreate(CreateView):
    model = Airport
    fields = AIRPORT_FIELDS


class AirportUpdate(UpdateView):
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

class PersonCreate(CreateView):
    model = Person
    fields = '__all__'

class PersonUpdate(UpdateView):
    model = Person
    fields = '__all__'
    pk_url_kwarg = 'person_id'

#------------------------------------------------------------

def all_events(request):
    '''List all events.'''

    all_events = Event.objects.order_by('slug')
    events = _get_pagination_items(request, all_events)
    for e in events:
        e.num_instructors = e.task_set.filter(role__name='instructor').count()
    context = {'title' : 'All Events',
               'all_events' : events}
    return render(request, 'workshops/all_events.html', context)


def event_details(request, event_slug):
    '''List details of a particular event.'''
    event = Event.objects.get(slug=event_slug)
    tasks = Task.objects.filter(event__id=event.id).order_by('role__name')
    context = {'title' : 'Event {0}'.format(event),
               'event' : event,
               'tasks' : tasks}
    return render(request, 'workshops/event.html', context)

def validate_event(request, event_slug):
    '''Check the event's home page *or* the specified URL (for testing).'''
    page_url, error_messages = None, []
    event = Event.objects.get(slug=event_slug)
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


def task_details(request, event_slug, person_id, role_name):
    '''List details of a particular task.'''
    task = Task.objects.get(event__slug=event_slug, person__id=person_id, role__name=role_name)
    context = {'title' : 'Task {0}'.format(task),
               'task' : task}
    return render(request, 'workshops/task.html', context)


class TaskCreate(CreateView):
    model = Task
    fields = TASK_FIELDS


class TaskUpdate(UpdateView):
    model = Task
    fields = TASK_FIELDS
    pk_url_kwarg = 'task_id'

    def get_object(self):
        """
        Returns the object the view is displaying.
        """

        event_slug = self.kwargs.get('event_slug', None)
        person_id = self.kwargs.get('person_id', None)
        role_name = self.kwargs.get('role_name', None)

        return get_object_or_404(Task, event__slug=event_slug, person__id=person_id, role__name=role_name)

#------------------------------------------------------------

COHORT_FIELDS = ['name', 'start', 'active', 'venue', 'qualifies']


def all_cohorts(request):
    '''List all cohorts.'''
    all_cohorts = Cohort.objects.order_by('start')
    user_can_add = request.user.has_perm('edit')
    context = {'title' : 'All Cohorts',
               'all_cohorts' : all_cohorts,
               'user_can_add' : user_can_add}
    return render(request, 'workshops/all_cohorts.html', context)


def cohort_details(request, cohort_name):
    '''List details of a particular cohort.'''
    cohort = Cohort.objects.get(name=cohort_name)
    trainees = Trainee.objects.filter(cohort_id=cohort.id)
    context = {'title' : 'Cohort {0}'.format(cohort),
               'cohort' : cohort,
               'trainees' : trainees}
    return render(request, 'workshops/cohort.html', context)


class CohortCreate(CreateView):
    model = Cohort
    fields = COHORT_FIELDS


class CohortUpdate(UpdateView):
    model = Cohort
    fields = COHORT_FIELDS
    slug_field = 'name'
    slug_url_kwarg = 'cohort_name'

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
            skills = []
            for s in Skill.objects.all():
                if form.cleaned_data[s.name]:
                    skills.append(s)
            persons = persons.have_skills(skills)

            # Add metadata which we will eventually filter by
            for person in persons:
                person.num_taught = \
                    person.task_set.filter(role__name='instructor').count()

            # Sort by location.
            loc = (float(form.cleaned_data['latitude']),
                   float(form.cleaned_data['longitude']))
            persons = [(earth_distance(loc, (p.airport.latitude, p.airport.longitude)), p)
                       for p in persons]
            persons.sort(
                key=lambda distance_person: (
                    distance_person[0],
                    distance_person[1].family,
                    distance_person[1].personal,
                    distance_person[1].middle))
            persons = [x[1] for x in persons[:10]]

        else:
            pass # FIXME: error message

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

    term, sites, events = '', None, None

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
        else:
            pass # FIXME: error message

    # if a GET (or any other method) we'll create a blank form
    else:
        form = SearchForm()

    context = {'title' : 'Search',
               'form': form,
               'term' : term,
               'sites' : sites,
               'events' : events}
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
