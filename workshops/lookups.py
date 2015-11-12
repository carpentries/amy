from django.contrib.auth.models import Group
from django.db.models import Q

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
class AdminLookup(ModelLookup):
    """The same as PersonLookup, but allows only to select administrators.

    Administrator is anyone with superuser power or in "administrators" group.
    """
    model = models.Person
    search_fields = (
        'personal__icontains',
        'family__icontains',
        'email__icontains',
        'username__icontains'
    )

    def get_query(self, request, term):
        results = super().get_query(request, term)
        admin_group = Group.objects.get(name='administrators')
        results = results.filter(
            Q(is_superuser=True) | Q(groups__in=[admin_group])
        )
        return results


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
registry.register(AdminLookup)
registry.register(AirportLookup)
