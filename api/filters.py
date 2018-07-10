from django_filters import rest_framework as filters

from workshops.filters import AMYFilterSet, TrainingRequestFilter
from workshops.models import Event, Task, Tag, Person, Badge


def filter_tag_by_name(queryset, name, values):
    tags = Tag.objects.filter(name__in=values)
    for tag in tags:
        queryset = queryset.filter(tags=tag)
    return queryset


class EventFilter(filters.FilterSet):
    start_after = filters.DateFilter(name='start', lookup_expr='gte')
    start_before = filters.DateFilter(name='start', lookup_expr='lte')
    end_after = filters.DateFilter(name='end', lookup_expr='gte')
    end_before = filters.DateFilter(name='end', lookup_expr='lte')
    TAG_CHOICES = Tag.objects.all().values_list('name', 'name')
    tag = filters.MultipleChoiceFilter(
        choices=TAG_CHOICES, name='tags', method=filter_tag_by_name,
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
    role = filters.CharFilter(name='role__name')

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

    class Meta:
        model = Person
        fields = (
            'badges', 'username', 'personal', 'middle', 'family', 'email',
            'may_contact', 'publish_profile', 'github',
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
    ids = IdInFilter(name='id', lookup_expr='in')

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
