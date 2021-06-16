from django_filters import rest_framework as filters

from consents.models import Consent, TermOption
from extrequests.filters import TrainingRequestFilter
from workshops.filters import NamesOrderingFilter
from workshops.models import Badge, Event, Person, Tag, Task


class EventFilter(filters.FilterSet):
    start_after = filters.DateFilter(field_name="start", lookup_expr="gte")
    start_before = filters.DateFilter(field_name="start", lookup_expr="lte")
    end_after = filters.DateFilter(field_name="end", lookup_expr="gte")
    end_before = filters.DateFilter(field_name="end", lookup_expr="lte")
    tags = filters.ModelMultipleChoiceFilter(
        field_name="tags__name",
        to_field_name="name",
        queryset=Tag.objects.all(),
        conjoined=True,
    )
    order_by = filters.OrderingFilter(
        fields=(
            "slug",
            "start",
            "end",
        ),
    )

    class Meta:
        model = Event
        fields = (
            "completed",
            "tags",
            "administrator",
            "host",
            "start",
            "start_before",
            "start_after",
            "end",
            "end_before",
            "end_after",
            "country",
        )


class TaskFilter(filters.FilterSet):
    role = filters.CharFilter(field_name="role__name")

    class Meta:
        model = Task
        fields = ("role",)


def filter_instructors(queryset, name, value):
    instructor_badges = Badge.objects.instructor_badges()
    if value is True:
        return queryset.filter(badges__in=instructor_badges)
    elif value is False:
        return queryset.exclude(badges__in=instructor_badges)
    else:
        return queryset


def filter_consent(queryset, name, value):
    if name == "may_contact":
        slug = "may-contact"
    elif name == "publish_profile":
        slug = "public-profile"
    else:
        raise NotImplementedError(f"Filter consent {name} not implemented")
    consents = Consent.objects.active().filter(
        term__slug=slug,
        person__in=queryset,
    )
    if value is True:
        option = TermOption.AGREE
    elif value is False:
        option = TermOption.DECLINE
    else:
        people_ids = consents.filter(term_option__isnull=True).values_list(
            "person_id", flat=True
        )
        return queryset.filter(person_id__in=people_ids)

    people_ids = consents.filter(term_option__option_type=option).values_list(
        "person_id", flat=True
    )
    return queryset.filter(pk__in=people_ids)


class PersonFilter(filters.FilterSet):
    is_instructor = filters.BooleanFilter(
        method=filter_instructors, label="Is instructor?"
    )

    may_contact = filters.BooleanFilter(method=filter_consent, label="May contact")
    publish_profile = filters.BooleanFilter(
        method=filter_consent, label="Consent to making profile public"
    )

    order_by = NamesOrderingFilter(
        fields=("email",),
    )

    class Meta:
        model = Person
        fields = (
            "badges",
            "username",
            "personal",
            "middle",
            "family",
            "email",
            "github",
            "country",
        )


class IdInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


class TrainingRequestFilterIDs(TrainingRequestFilter):
    ids = IdInFilter(field_name="id", lookup_expr="in")

    class Meta(TrainingRequestFilter.Meta):
        fields = [
            "ids",
            "search",
            "group_name",
            "state",
            "matched",
            "affiliation",
            "location",
        ]
