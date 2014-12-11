from django.shortcuts import render
from workshops.models import Site, Event, Person, Cohort
from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import get_object_or_404

def index(request):
    '''Home page.'''
    upcoming_events = Event.objects.upcoming_events()
    context = {'title' : 'Home Page',
               'upcoming_events' : upcoming_events}
    return render(request, 'workshops/index.html', context)

#------------------------------------------------------------

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
    fields = ['domain', 'fullname', 'country']

class SiteUpdate(UpdateView):
    model = Site
    fields = ['domain', 'fullname', 'country']
    slug_field = 'domain'
    slug_url_kwarg = 'site_domain'

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
    context = {'title' : 'All Events',
               'all_events' : all_events}
    return render(request, 'workshops/all_events.html', context)

def event_details(request, event_slug):
    '''List details of a particular event.'''
    event = Event.objects.get(slug=event_slug)
    context = {'title' : 'Event {0}'.format(event),
               'event' : event}
    return render(request, 'workshops/event.html', context)

#------------------------------------------------------------

def all_cohorts(request):
    '''List all cohorts.'''
    all_cohorts = Cohort.objects.order_by('start')
    user_can_add = request.user.has_perm('workshops.add_cohort')
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
    fields = ['name', 'start', 'active', 'venue', 'qualifies']

class CohortUpdate(UpdateView):
    model = Cohort
    fields = ['name', 'start', 'active', 'venue', 'qualifies']
    slug_field = 'name'
    slug_url_kwarg = 'cohort_name'

