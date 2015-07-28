from selectable.base import ModelLookup
from selectable.registry import registry
from selectable.decorators import login_required

from workshops import models


@login_required
class EventLookup(ModelLookup):
    model = models.Event
    search_fields = ('slug__icontains', )


@login_required
class HostLookup(ModelLookup):
    model = models.Host
    search_fields = (
        'domain__icontains',
        'fullname__icontains'
    )


@login_required
class PersonLookup(ModelLookup):
    model = models.Person
    search_fields = (
         'personal__icontains',
         'family__icontains',
         'email__icontains',
         'username__icontains'
    )


@login_required
class AirportLookup(ModelLookup):
    model = models.Airport
    search_fields = (
        'iata__icontains',
        'fullname__icontains'
    )


registry.register(EventLookup)
registry.register(HostLookup)
registry.register(PersonLookup)
registry.register(AirportLookup)
