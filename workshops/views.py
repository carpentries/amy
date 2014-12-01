from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    '''Home page.'''
    return HttpResponse('Home page rendered')

def all_sites(request):
    '''List all sites.'''
    return HttpResponse('All sites rendered')

def site_details(request, site_domain):
    '''List details of a particular site.'''
    return HttpResponse('Site details for {0}'.format(site_domain))
