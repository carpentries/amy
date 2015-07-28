import django_filters

from workshops.models import Event, Host, Person, Task, Airport


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
        self.extra['choices'].insert(0, (None, '---------'))
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
            return getattr(qs, "{}_events".format(value))()
        except AttributeError:
            return qs


class EventFilter(django_filters.FilterSet):
    host = ForeignKeyAllValuesFilter(Host)
    administrator = ForeignKeyAllValuesFilter(Host)

    STATUS_CHOICES = [
        ('', 'All'),
        ('past', 'Past'),
        ('ongoing', 'Ongoing'),
        ('upcoming', 'Upcoming'),
        ('unpublished', 'Unpublished'),
        ('uninvoiced', 'Uninvoiced'),
    ]
    status = EventStateFilter(choices=STATUS_CHOICES)

    class Meta:
        model = Event
        fields = [
            'tags',
            'host',
            'administrator',
            'invoiced',
        ]
        order_by = ['-slug', 'slug', 'start', '-start', 'end', '-end']


class HostFilter(django_filters.FilterSet):
    # it's tricky to properly filter by countries from django-countries, so
    # only allow filtering by 2-char names from DB
    country = django_filters.AllValuesFilter()

    class Meta:
        model = Host
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


class TaskFilter(django_filters.FilterSet):
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


class AirportFilter(django_filters.FilterSet):
    fullname = django_filters.CharFilter(lookup_type='icontains')

    class Meta:
        model = Airport
        fields = [
            'fullname',
        ]
        order_by = ["iata", "-iata", "fullname", "-fullname"]
