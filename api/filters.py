import django_filters
from rest_framework import filters

from workshops.models import Event, Task, Tag


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
        fields = [
            'completed', 'tag',
            'start', 'start_before', 'start_after',
            'end', 'end_before', 'end_after',
        ]
        order_by = ['-slug', 'slug', 'start', '-start', 'end', '-end']


class TaskFilter(filters.FilterSet):
    role = django_filters.CharFilter(name='role__name')

    class Meta:
        model = Task
        fields = [
            'role'
        ]
