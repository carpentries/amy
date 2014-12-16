from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import CreateView, UpdateView

from workshops.models import Site, Airport, Event, Person, Task, Cohort
from workshops.forms import InstructorMatchForm
from workshops.util import earth_distance

#------------------------------------------------------------

ITEMS_PER_PAGE = 25

#------------------------------------------------------------

def index(request):
    '''Home page.'''
    upcoming_events = Event.objects.upcoming_events()
    context = {'title' : 'Home Page',
               'upcoming_events' : upcoming_events}
    return render(request, 'workshops/index.html', context)

#------------------------------------------------------------

SITE_FIELDS = ['domain', 'fullname', 'country']

def all_sites(request):
    '''List all sites.'''
    all_sites = Site.objects.order_by('domain')
    user_can_add = request.user.has_perm('edit')
    context = {'title' : 'All Sites',
               'all_sites' : all_sites,
               'user_can_add' : user_can_add}
    return render(request, 'workshops/all_sites.html', context)

def site_details(request, site_domain):
    '''List details of a particular site.'''
    site = Site.objects.get(domain=site_domain)
    context = {'title' : 'Site {0}'.format(site),
               'site' : site}
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
    context = {'title' : 'All Persons',
               'all_persons' : all_persons}
    return render(request, 'workshops/all_persons.html', context)

def person_details(request, person_id):
    '''List details of a particular person.'''
    person = Person.objects.get(id=person_id)
    context = {'title' : 'Person {0}'.format(person),
               'person' : person}
    return render(request, 'workshops/person.html', context)

#------------------------------------------------------------

def all_events(request):
    '''List all events.'''

    all_events = Event.objects.order_by('slug')

    # Get the number of items requested per page, default to 25
    # This is important for unit testing, we need to be
    # able to specify how many items to expect
    items = request.GET.get('items_per_page', ITEMS_PER_PAGE)

    # Only paginate if the number of items is not 'all'
    if not items == 'all':

        # If items is not an integer, set it to the default
        try:
            items = int(items)
        except ValueError:
            items = ITEMS_PER_PAGE

        events_paginator = Paginator(all_events, items)

        # Get the page number requested, if any
        page = request.GET.get('page')

        try:
            events = events_paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            events = events_paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            events = events_paginator.page(events_paginator.num_pages)
    else:
        events = all_events

    context = {'title' : 'All Events',
               'all_events' : events}

    return render(request, 'workshops/all_events.html', context)

def event_details(request, event_slug):
    '''List details of a particular event.'''
    event = Event.objects.get(slug=event_slug)
    context = {'title' : 'Event {0}'.format(event),
               'event' : event}
    return render(request, 'workshops/event.html', context)

#------------------------------------------------------------

TASK_FIELDS = ['event', 'person', 'role']

def all_tasks(request):
    '''List all tasks.'''
    all_tasks = Task.objects.order_by('event', 'person', 'role')
    user_can_add = request.user.has_perm('edit')
    context = {'title' : 'All Tasks',
               'all_tasks' : all_tasks,
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
    context = {'title' : 'Cohort {0}'.format(cohort),
               'cohort' : cohort}
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

def match(request):
    persons = None

    if request.method == 'POST':
        form = InstructorMatchForm(request.POST)
        if form.is_valid():
            loc = (float(form.cleaned_data['latitude']),
                   float(form.cleaned_data['longitude']))
            persons = Person.objects.filter(airport__isnull=False)
            persons = [(earth_distance(loc, (p.airport.latitude, p.airport.longitude)), p)
                       for p in persons]
            persons.sort()
            persons = persons[:10]
            persons = [x[1] for x in persons]
        else:
            pass # FIXME: error message

    # if a GET (or any other method) we'll create a blank form
    else:
        form = InstructorMatchForm()

    return render(request, 'workshops/match.html', {'form': form, 'persons' : persons})
