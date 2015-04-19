from selectable.base import ModelLookup
from selectable.registry import registry

from . import models


class EventLookup(ModelLookup):
    model = models.Event
    search_fields = ('slug__icontains', )


class SiteLookup(ModelLookup):
    model = models.Site
    search_fields = ('domain__icontains', )


class PersonLookup(ModelLookup):
    model = models.Person
    search_fields = (
         'personal__icontains',
         'family__icontains',
         'email__icontains',
         'username__icontains'
    )


class AirportLookup(ModelLookup):
    model = models.Airport
    search_fields = (
        'iata__icontains',
        'fullname__icontains'
    )


registry.register(EventLookup)
registry.register(SiteLookup)
registry.register(PersonLookup)
registry.register(AirportLookup)
