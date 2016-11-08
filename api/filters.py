import django_filters
from rest_framework import filters

from workshops.filters import AMYFilterSet
from workshops.models import Event, Task, Tag, Person, Badge


def filter_tag_by_name(queryset, values):
    tags = Tag.objects.filter(name__in=values)
    for tag in tags:
        queryset = queryset.filter(tags=tag)
    return queryset


class EventFilter(filters.FilterSet):
    start_after = django_filters.DateFilter(name='start', lookup_type='gte')
    start_before = django_filters.DateFilter(name='start', lookup_type='lte')
    end_after = django_filters.DateFilter(name='end', lookup_type='gte')
    end_before = django_filters.DateFilter(name='end', lookup_type='lte')
    TAG_CHOICES = Tag.objects.all().values_list('name', 'name')
    tag = django_filters.MultipleChoiceFilter(
        choices=TAG_CHOICES, name='tags', action=filter_tag_by_name,
    )

    class Meta:
        model = Event
        fields = (
            'completed', 'tag',
            'start', 'start_before', 'start_after',
            'end', 'end_before', 'end_after',
        )
        order_by = ('-slug', 'slug', 'start', '-start', 'end', '-end')


class TaskFilter(filters.FilterSet):
    role = django_filters.CharFilter(name='role__name')

    class Meta:
        model = Task
        fields = (
            'role',
        )


def filter_instructors(queryset, value):
    instructor_badges = Badge.objects.instructor_badges()
    if value is True:
        return queryset.filter(badges__in=instructor_badges)
    elif value is False:
        return queryset.exclude(badges__in=instructor_badges)
    else:
        return queryset


class PersonFilter(filters.FilterSet):
    is_instructor = django_filters.BooleanFilter(action=filter_instructors)

    class Meta:
        model = Person
        fields = (
            'badges', 'username', 'personal', 'middle', 'family', 'email',
            'may_contact',
        )
        order_by = (
            'lastname', '-lastname', 'firstname', '-firstname', 'email',
            '-email',
        )

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


class InstructorsOverTimeFilter(AMYFilterSet):
    badges = django_filters.ModelMultipleChoiceFilter(
        queryset=Badge.objects.instructor_badges(),
        label='Badges',
        lookup_type='in',
    )

    class Meta:
        model = Person
        fields = [
            'badges',
        ]


class WorkshopsOverTimeFilter(AMYFilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label='Events with at least one of the following tags:',
    )

    class Meta:
        model = Event
        fields = [
            'tags',
        ]


class LearnersOverTimeFilter(AMYFilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label='Events with all the following tags:',
        conjoined=True,
    )

    class Meta:
        model = Event
        fields = [
            'tags',
        ]
