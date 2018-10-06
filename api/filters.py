from django_filters import rest_framework as filters

from workshops.filters import (
    AMYFilterSet,
    TrainingRequestFilter,
    NamesOrderingFilter,
)
from workshops.models import Event, Task, Tag, Person, Badge


def filter_tag_by_name(queryset, name, values):
    # tags = Tag.objects.filter(name__in=values)
    # for tag in tags:
    #     queryset = queryset.filter(tags=tag)
    # return queryset
    return Tag.objects.all()


class EventFilter(filters.FilterSet):
    start_after = filters.DateFilter(field_name='start', lookup_expr='gte')
    start_before = filters.DateFilter(field_name='start', lookup_expr='lte')
    end_after = filters.DateFilter(field_name='end', lookup_expr='gte')
    end_before = filters.DateFilter(field_name='end', lookup_expr='lte')
    TAG_CHOICES = Tag.objects.all().values_list('name', 'name')
    tag = filters.MultipleChoiceFilter(
        choices=TAG_CHOICES, field_name='tags', method=filter_tag_by_name,
    )
    order_by = filters.OrderingFilter(
        fields=(
            'slug',
            'start',
            'end',
        ),
    )

    class Meta:
        model = Event
        fields = (
            'completed', 'tag',
            'administrator', 'host',
            'start', 'start_before', 'start_after',
            'end', 'end_before', 'end_after',
            'country',
        )


class TaskFilter(filters.FilterSet):
    role = filters.CharFilter(field_name='role__name')

    class Meta:
        model = Task
        fields = (
            'role',
        )


def filter_instructors(queryset, name, value):
    instructor_badges = Badge.objects.instructor_badges()
    if value is True:
        return queryset.filter(badges__in=instructor_badges)
    elif value is False:
        return queryset.exclude(badges__in=instructor_badges)
    else:
        return queryset


class PersonFilter(filters.FilterSet):
    is_instructor = filters.BooleanFilter(method=filter_instructors,
                                          label='Is instructor?')

    order_by = NamesOrderingFilter(
        fields=(
            'email',
        ),
    )

    class Meta:
        model = Person
        fields = (
            'badges', 'username', 'personal', 'middle', 'family', 'email',
            'may_contact', 'publish_profile', 'github', 'country',
        )


class InstructorsOverTimeFilter(AMYFilterSet):
    badges = filters.ModelMultipleChoiceFilter(
        queryset=Badge.objects.instructor_badges(),
        label='Badges',
        lookup_expr='in',
    )

    class Meta:
        model = Person
        fields = [
            'badges',
        ]


class WorkshopsOverTimeFilter(AMYFilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label='Events with at least one of the following tags:',
    )

    class Meta:
        model = Event
        fields = [
            'tags',
        ]


class LearnersOverTimeFilter(AMYFilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label='Events with all the following tags:',
        conjoined=True,
    )

    class Meta:
        model = Event
        fields = [
            'tags',
        ]


class IdInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


class TrainingRequestFilterIDs(TrainingRequestFilter):
    ids = IdInFilter(field_name='id', lookup_expr='in')

    class Meta(TrainingRequestFilter.Meta):
        fields = [
            'ids',
            'search',
            'group_name',
            'state',
            'matched',
            'affiliation',
            'location',
        ]
