import django_filters
from django_countries.widgets import CountrySelectWidget

from workshops.models import Event, Site, Person, Airport


class EventFilter(django_filters.FilterSet):
    class Meta:
        model = Event
        fields = [
            'published',
            'tags',
            'site',
            'organizer',
            'invoiced',
        ]
        order_by = ['slug', '-slug', 'start', '-start', 'end', '-end']


class SiteFilter(django_filters.FilterSet):
    # it's tricky to properly filter by countries from django-countries, so
    # only allow filtering by 2-char names from DB
    country = django_filters.AllValuesFilter()

    class Meta:
        model = Site
        fields = [
            'country',
        ]
        order_by = ['fullname', '-fullname', 'domain', '-domain', ]


class PersonFilter(django_filters.FilterSet):
    class Meta:
        model = Person
        fields = [
            'badges',
        ]
        order_by = ["lastname", "-lastname", "firstname", "-firstname",
                    "email", "-email"]

    def get_order_by(self, order_value):
        if order_value == 'firstname':
            return ['personal', 'middle', 'family']
        elif order_value == '-firstname':
            return ['-personal', '-middle', '-family']
        elif order_value == 'lastname':
            return ['family', 'middle', 'personal']
        elif order_value == '-lastname':
            return ['-family', '-middle', '-personal']
        return super().get_order_by(order_value)
