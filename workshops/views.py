from django.shortcuts import render
from workshops.models import Site, Event, Person

def index(request):
    '''Home page.'''
    context = {}
    return render(request, 'workshops/index.html', context)

#------------------------------------------------------------

def all_sites(request):
    '''List all sites.'''
    all_sites = Site.objects.order_by('domain')
    context = {'all_sites' : all_sites}
    return render(request, 'workshops/all_sites.html', context)

def site_details(request, site_domain):
    '''List details of a particular site.'''
    site = Site.objects.get(domain=site_domain)
    context = {'site' : site}
    return render(request, 'workshops/site.html', context)

#------------------------------------------------------------

def all_persons(request):
    '''List all persons.'''
    all_persons = Person.objects.order_by('family', 'personal')
    context = {'all_persons' : all_persons}
    return render(request, 'workshops/all_persons.html', context)

def person_details(request, person_id):
    '''List details of a particular person.'''
    person = Person.objects.get(id=person_id)
    context = {'person' : person}
    return render(request, 'workshops/person.html', context)

#------------------------------------------------------------

def all_events(request):
    '''List all events.'''
    all_events = Event.objects.order_by('slug')
    context = {'all_events' : all_events}
    return render(request, 'workshops/all_events.html', context)

def event_details(request, event_slug):
    '''List details of a particular event.'''
    event = Event.objects.get(slug=event_slug)
    context = {'event' : event}
    return render(request, 'workshops/event.html', context)

