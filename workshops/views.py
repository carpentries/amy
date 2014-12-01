from django.shortcuts import render
from django.http import HttpResponse
from workshops.models import Site

def index(request):
    '''Home page.'''
    context = {}
    return render(request, 'workshops/index.html', context)

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

