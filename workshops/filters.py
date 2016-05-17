import django.forms.widgets

import django_filters
from django_countries import Countries

from workshops.models import (
    Event,
    Host,
    Person,
    Airport,
    EventRequest,
    Tag,
    Task,
    Award,
    InvoiceRequest,
    EventSubmission,
)

EMPTY_SELECTION = (None, '---------')


class AllCountriesFilter(django_filters.ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct()
        qs = qs.order_by(self.name).values_list(self.name, flat=True)

        choices = [o for o in qs if o]
        countries = Countries()
        countries.only = choices

        self.extra['choices'] = list(countries)
        self.extra['choices'].insert(0, EMPTY_SELECTION)
        return super().field


class ForeignKeyAllValuesFilter(django_filters.ChoiceFilter):
    def __init__(self, model, *args, **kwargs):
        self.lookup_model = model
        super().__init__(*args, **kwargs)

    @property
    def field(self):
        name = self.name
        model = self.lookup_model

        qs1 = self.model._default_manager.distinct()
        qs1 = qs1.order_by(name).values_list(name, flat=True)
        qs2 = model.objects.filter(pk__in=qs1)
        self.extra['choices'] = [(o.pk, str(o)) for o in qs2]
        self.extra['choices'].insert(0, EMPTY_SELECTION)
        return super().field


class EventStateFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if isinstance(value, django_filters.fields.Lookup):
            value = value.value

        # no filtering
        if value in ([], (), {}, None, '', 'all'):
            return qs

        # no need to check if value exists in self.extra['choices'] because
        # validation is done by django_filters
        try:
            return getattr(qs, value)()
        except AttributeError:
            return qs


class FilterSetWithoutHelpText(django_filters.FilterSet):
    """Because of some stupidity this got merged to django-filters:
    https://github.com/alex/django-filter/commit/90d244b

    What it does is it adds a help_text to ALL filters!!!
    In this class I try to remove it from every field. The solution:
    https://github.com/alex/django-filter/pull/136#issuecomment-135602792
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for key in self.filters.items():
            self.filters[key[0]].extra.update({'help_text': ''})


class EventFilter(FilterSetWithoutHelpText):
    assigned_to = ForeignKeyAllValuesFilter(Person)
    host = ForeignKeyAllValuesFilter(Host)
    administrator = ForeignKeyAllValuesFilter(Host)

    STATUS_CHOICES = [
        ('', 'All'),
        ('active', 'Active'),
        ('past_events', 'Past'),
        ('ongoing_events', 'Ongoing'),
        ('upcoming_events', 'Upcoming'),
        ('unpublished_events', 'Unpublished'),
        ('published_events', 'Published'),
        ('uninvoiced_events', 'Uninvoiced'),
        ('metadata_changed', 'Detected changes in tags'),
    ]
    status = EventStateFilter(choices=STATUS_CHOICES)

    invoice_status = django_filters.ChoiceFilter(
        choices=(EMPTY_SELECTION, ) + Event.INVOICED_CHOICES,
    )

    class Meta:
        model = Event
        fields = [
            'assigned_to',
            'tags',
            'host',
            'administrator',
            'invoice_status',
            'completed',
        ]
        order_by = ['-slug', 'slug', 'start', '-start', 'end', '-end']


def filter_active_eventrequest(qs, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class EventRequestFilter(FilterSetWithoutHelpText):
    assigned_to = ForeignKeyAllValuesFilter(Person)
    country = AllCountriesFilter()
    active = django_filters.ChoiceFilter(
        choices=(('all', 'All'), ('true', 'Open'), ('false', 'Closed')),
        label='Status', action=filter_active_eventrequest,
        widget=django.forms.widgets.RadioSelect,
    )
    workshop_type = django_filters.ChoiceFilter(
        choices=(('', 'All'), ('swc', 'Software-Carpentry'),
                 ('dc', 'Data-Carpentry')),
        label='Workshop type',
        widget=django.forms.widgets.RadioSelect,
    )

    class Meta:
        model = EventRequest
        fields = [
            'assigned_to',
            'workshop_type',
            'active',
            'country',
        ]
        order_by = ['-created_at', 'created_at']


class HostFilter(FilterSetWithoutHelpText):
    country = AllCountriesFilter()

    class Meta:
        model = Host
        fields = [
            'country',
        ]
        order_by = ['fullname', '-fullname', 'domain', '-domain', ]


def filter_taught_workshops(queryset, values):
    """Limit Persons to only instructors from events with specific tags.

    This needs to be in a separate function because django-filters doesn't
    support `action` parameter as supposed, ie. with
    `action='filter_taught_workshops'` it doesn't call the method; instead it
    tries calling a string, which results in error."""
    if not values:
        return queryset

    return queryset.filter(task__role__name='instructor') \
                   .filter(task__event__tags__in=values) \
                   .distinct()


class PersonFilter(FilterSetWithoutHelpText):
    taught_workshops = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(), label='Taught at workshops of type',
        action=filter_taught_workshops,
    )

    class Meta:
        model = Person
        fields = [
            'badges', 'taught_workshops',
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


class TaskFilter(FilterSetWithoutHelpText):
    class Meta:
        model = Task
        fields = [
            'event',
            # can't filter on person because person's name contains 3 fields:
            # person.personal, person.middle, person.family
            # 'person',
            'role',
        ]
        order_by = [
            ['event__slug', 'Event'],
            ['-event__slug', 'Event (descending)'],
            ['person__family', 'Person'],
            ['-person__family', 'Person (descending)'],
            ['role', 'Role'],
            ['-role', 'Role (descending)'],
        ]


class AirportFilter(FilterSetWithoutHelpText):
    fullname = django_filters.CharFilter(lookup_type='icontains')

    class Meta:
        model = Airport
        fields = [
            'fullname',
        ]
        order_by = ["iata", "-iata", "fullname", "-fullname"]


class BadgeAwardsFilter(FilterSetWithoutHelpText):
    awarded_after = django_filters.DateFilter(name='awarded',
                                              lookup_type='gte')
    awarded_before = django_filters.DateFilter(name='awarded',
                                               lookup_type='lte')

    class Meta:
        model = Award
        fields = (
            'awarded_after', 'awarded_before', 'event',
        )
        order_by = [
            '-awarded', 'awarded', '-person__family',
            'person__family',
        ]


class InvoiceRequestFilter(FilterSetWithoutHelpText):
    STATUS_CHOICES = (('', 'All'),) + InvoiceRequest.STATUS_CHOICES
    status = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES,
        widget=django.forms.widgets.RadioSelect,
    )

    class Meta:
        model = InvoiceRequest
        fields = [
            'status',
            'organization',
        ]
        order_by = [
            '-event__slug', 'event__slug',
            'organization__domain', '-organization__domain',
        ]


def filter_active_eventsubmission(qs, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class EventSubmissionFilter(FilterSetWithoutHelpText):
    active = django_filters.ChoiceFilter(
        choices=(('', 'All'), ('true', 'Open'), ('false', 'Closed')),
        label='Status', action=filter_active_eventsubmission,
        widget=django.forms.widgets.RadioSelect,
    )
    assigned_to = ForeignKeyAllValuesFilter(Person)

    class Meta:
        model = EventSubmission
        fields = [
            'active',
            'assigned_to',
        ]
        order_by = [
            '-created_at', 'created_at',
        ]
