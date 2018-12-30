from django.forms import widgets
from django_filters import rest_framework as filters
from django_filters import widgets as filter_widgets
from django_countries import Countries

from extrequests.filters import (
    TrainingRequestFilter,
)
from workshops.fields import (
    Select2Multiple,
)
from workshops.filters import (
    AMYFilterSet,
    NamesOrderingFilter,
)
from workshops.models import Event, Task, Tag, Person, Badge


class EventFilter(filters.FilterSet):
    start_after = filters.DateFilter(field_name='start', lookup_expr='gte')
    start_before = filters.DateFilter(field_name='start', lookup_expr='lte')
    end_after = filters.DateFilter(field_name='end', lookup_expr='gte')
    end_before = filters.DateFilter(field_name='end', lookup_expr='lte')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        queryset=Tag.objects.all(),
        conjoined=True,
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
            'completed', 'tags',
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
    country = filters.MultipleChoiceFilter(
        choices=list(Countries()),
        widget=Select2Multiple(),
        help_text="Instructor's country",
    )
    date = filters.DateFromToRangeFilter(
        label='Date range (from - to)',
        help_text="Filters on award's date",
        widget=filter_widgets.RangeWidget(attrs={"class": "dateinput"}),
    )

    class Meta:
        model = Person
        fields = [
            'badges', 'country',
        ]


class WorkshopsOverTimeFilter(AMYFilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label='Events with at least one of the following tags:',
        widget=widgets.SelectMultiple(attrs=dict(size=13)),
    )
    country = filters.MultipleChoiceFilter(
        choices=list(Countries()),
        widget=Select2Multiple(),
    )
    start = filters.DateFromToRangeFilter(
        label='Date range (from - to)',
        help_text="Filters only on the 'Event.start' field",
        widget=filter_widgets.RangeWidget(attrs={"class": "dateinput"}),
    )

    class Meta:
        model = Event
        fields = [
            'tags', 'country', 'start',
        ]


class LearnersOverTimeFilter(AMYFilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label='Events with all the following tags:',
        conjoined=True,
        widget=widgets.SelectMultiple(attrs=dict(size=13)),
    )
    country = filters.MultipleChoiceFilter(
        choices=list(Countries()),
        widget=Select2Multiple(),
    )
    start = filters.DateFromToRangeFilter(
        label='Date range (from - to)',
        help_text="Filters only on the 'Event.start' field",
        widget=filter_widgets.RangeWidget(attrs={"class": "dateinput"}),
    )

    class Meta:
        model = Event
        fields = [
            'tags', 'country', 'start',
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
