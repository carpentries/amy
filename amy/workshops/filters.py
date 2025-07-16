from typing import Any, Sequence, Union

from django.conf import settings
from django.db.models import Model, Q, QuerySet
from django.forms import Field, widgets
from django_countries import Countries
import django_filters

from dashboard.models import Continent
from workshops.fields import (
    ModelSelect2MultipleWidget,
    ModelSelect2Widget,
    Select2Widget,
)
from workshops.forms import SELECT2_SIDEBAR, bootstrap_helper_filter
from workshops.mixins import StateMixin
from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    KnowledgeDomain,
    Language,
    Lesson,
    Organization,
    Person,
    Tag,
    Task,
)


def extend_country_choices(
    choices: Sequence[str], countries_override: dict[str, Any]
) -> list[Union[str, tuple[str, Any]]]:
    """Update countries with overrides from settings.

    This is useful in case we're setting `only` for list of countries in
    Django-Countries. Then custom choices provided need to have a tuple (code, name)
    format, which is grabbed from COUNTRIES_OVERRIDE setting.

    For example this: ['AZ', 'BA', 'BY', 'FM', 'GD', 'W3']  # W3 is custom
    will be changes to this: ['AZ', 'BA', 'BY', 'FM', 'GD', ('W3', 'Online')]
    """
    countries: list[Union[str, tuple[str, str]]] = list(choices)
    common: set[str] = countries_override.keys() & set(choices)
    for country in common:
        countries.remove(country)
        countries.append((country, countries_override[country]))
    return countries


class BaseCountriesFilter(django_filters.Filter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.extend_countries = kwargs.pop("extend_countries", True)
        super().__init__(*args, **kwargs)  # type: ignore

    def _get_countries(self) -> list[str]:
        qs = self.model._default_manager.distinct()  # type: ignore
        qs = qs.order_by(self.field_name).values_list(self.field_name, flat=True)
        choices = [o for o in qs if o]
        return choices

    @property
    def field(self) -> Field:
        choices = self._get_countries()
        if self.extend_countries:
            only = extend_country_choices(choices, settings.COUNTRIES_OVERRIDE)
        else:
            only = {abbrv: name for abbrv, name in Countries().countries.items() if abbrv in choices}  # type: ignore

        countries = Countries()
        countries.only = only  # type: ignore
        self.extra["choices"] = list(countries)
        return super().field  # type: ignore


class AllCountriesFilter(BaseCountriesFilter, django_filters.ChoiceFilter):
    pass


class AllCountriesMultipleFilter(BaseCountriesFilter, django_filters.MultipleChoiceFilter):
    pass


class ForeignKeyAllValuesFilter(django_filters.ChoiceFilter):
    def __init__(self, model: type[Model], *args: Any, **kwargs: Any) -> None:
        self.lookup_model = model
        super().__init__(*args, **kwargs)  # type: ignore

    @property
    def field(self) -> Field:
        name = self.field_name
        model = self.lookup_model

        qs1 = self.model._default_manager.distinct()  # type: ignore
        qs1 = qs1.order_by(name).values_list(name, flat=True)
        qs2 = model.objects.filter(pk__in=qs1)  # type: ignore
        self.extra["choices"] = [(o.pk, str(o)) for o in qs2]
        return super().field  # type: ignore


class EventStateFilter(django_filters.ChoiceFilter):
    def filter(self, qs: QuerySet[Model], value: Any) -> QuerySet[Model]:
        if isinstance(value, django_filters.fields.Lookup):
            value = value.value

        # no filtering
        if value in ([], (), {}, None, "", "all"):
            return qs

        # no need to check if value exists in self.extra['choices'] because
        # validation is done by django_filters
        try:
            return getattr(qs, value)()  # type: ignore
        except AttributeError:
            return qs


class NamesOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.extra["choices"] += [
            ("lastname", "Last name"),
            ("-lastname", "Last name (descending)"),
            ("firstname", "First name"),
            ("-firstname", "First name (descending)"),
        ]

    def filter(self, qs: QuerySet[Model], value: list[Any] | None) -> QuerySet[Model]:
        if not value:
            return super().filter(qs, value)  # type: ignore
        elif any(v in ["lastname"] for v in value):
            return super().filter(qs, ("family", "middle", "personal"))  # type: ignore
        elif any(v in ["-lastname"] for v in value):
            return super().filter(qs, ("-family", "-middle", "-personal"))  # type: ignore
        elif any(v in ["firstname"] for v in value):
            return super().filter(qs, ("personal", "middle", "family"))  # type: ignore
        elif any(v in ["-firstname"] for v in value):
            return super().filter(qs, ("-personal", "-middle", "-family"))  # type: ignore
        else:
            return super().filter(qs, value)  # type: ignore


class ContinentFilter(django_filters.ChoiceFilter):
    @property
    def field(self) -> Field:
        self.extra["choices"] = Continent.objects.values_list("pk", "name")
        return super().field  # type: ignore

    def filter(self, qs: QuerySet[Model], value: Any) -> QuerySet[Model]:
        if isinstance(value, django_filters.fields.Lookup):
            value = value.value

        # no filtering
        if value in ([], (), {}, None, "", "all"):
            return qs

        # filtering: qs `country` must be in the list of countries given by
        # selected continent
        return qs.filter(country__in=Continent.objects.get(pk=value).countries)


# ------------------------------------------------------------


class AMYFilterSet(django_filters.FilterSet):  # type: ignore
    """
    This base class sets FormHelper.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Set default FormHelper
        self.form.helper = bootstrap_helper_filter


class StateFilterSet(django_filters.FilterSet):  # type: ignore
    """A mixin for extending filter classes for Django models that make use of
    `StateMixin`."""

    state = django_filters.ChoiceFilter(
        choices=StateMixin.STATE_CHOICES,
        label="State",
        widget=widgets.RadioSelect,
        empty_label="Any",
        null_label=None,
        null_value=None,
    )  # type: ignore


# ------------------------------------------------------------


class EventFilter(AMYFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2Widget)
    host = ForeignKeyAllValuesFilter(Organization, widget=Select2Widget)
    administrator = ForeignKeyAllValuesFilter(Organization, widget=Select2Widget)

    STATUS_CHOICES = [
        ("", "All"),
        ("active", "Active"),
        ("past_events", "Past"),
        ("ongoing_events", "Ongoing"),
        ("upcoming_events", "Upcoming"),
        ("unpublished_events", "Unpublished"),
        ("published_events", "Published"),
        ("metadata_changed", "Detected changes in metadata"),
    ]
    state = EventStateFilter(choices=STATUS_CHOICES, label="Status", widget=Select2Widget)  # type: ignore

    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label="Tags",
        widget=ModelSelect2MultipleWidget(
            data_view="tag-lookup",
        ),
    )  # type: ignore

    country = AllCountriesFilter(widget=Select2Widget)
    continent = ContinentFilter(widget=Select2Widget, label="Continent")  # type: ignore

    order_by = django_filters.OrderingFilter(
        fields=(
            "slug",
            "start",
            "end",
        ),
    )  # type: ignore

    class Meta:
        model = Event
        fields = [
            "assigned_to",
            "tags",
            "host",
            "administrator",
            "completed",
            "country",
            "continent",
        ]


class EventCategoryFilter(AMYFilterSet):
    active = django_filters.BooleanFilter("active")  # type: ignore
    order_by = django_filters.OrderingFilter(
        fields=(
            "name",
            "description",
            "created_at",
            "last_modified_at",
        )
    )  # type: ignore


def filter_taught_workshops(queryset: QuerySet[Person], name: str, values: list[str]) -> QuerySet[Person]:
    """Limit Persons to only instructors from events with specific tags.

    This needs to be in a separate function because django-filters doesn't
    support `action` parameter as supposed, ie. with
    `method='filter_taught_workshops'` it doesn't call the method; instead it
    tries calling a string, which results in error."""

    if not values:
        return queryset

    return queryset.filter(task__role__name="instructor", task__event__tags__in=values).distinct()


class PersonFilter(AMYFilterSet):
    badges = django_filters.ModelMultipleChoiceFilter(
        queryset=Badge.objects.all(),
        label="Badges",
        widget=ModelSelect2MultipleWidget(
            data_view="badge-lookup",
        ),
    )  # type: ignore
    taught_workshops = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label="Taught at workshops of type",
        method=filter_taught_workshops,
        widget=ModelSelect2MultipleWidget(
            data_view="tag-lookup",
        ),
    )  # type: ignore

    order_by = NamesOrderingFilter(
        fields=("email",),
    )

    class Meta:
        model = Person
        fields = [
            "badges",
            "taught_workshops",
        ]


class TaskFilter(AMYFilterSet):
    event = django_filters.ModelChoiceFilter(
        queryset=Event.objects.all(),
        label="Event",
        widget=ModelSelect2Widget(
            data_view="event-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )  # type: ignore

    order_by = django_filters.OrderingFilter(
        fields=(
            ("event__slug", "event"),
            ("person__family", "person"),
            ("role", "role"),
        ),
        field_labels={
            "event__slug": "Event",
            "person__family": "Person",
            "role": "Role",
        },
    )  # type: ignore

    class Meta:
        model = Task
        fields = [
            "event",
            # can't filter on person because person's name contains 3 fields:
            # person.personal, person.middle, person.family
            # 'person',
            "role",
        ]


class AirportFilter(AMYFilterSet):
    fullname = django_filters.CharFilter(lookup_expr="icontains")  # type: ignore

    continent = ContinentFilter(widget=Select2Widget, label="Continent")  # type: ignore

    order_by = django_filters.OrderingFilter(
        fields=(
            "iata",
            "fullname",
        ),
        field_labels={
            "iata": "IATA",
            "fullname": "Full name",
        },
    )  # type: ignore

    class Meta:
        model = Airport
        fields = [
            "fullname",
        ]


class BadgeAwardsFilter(AMYFilterSet):
    awarded_after = django_filters.DateFilter(field_name="awarded", lookup_expr="gte")  # type: ignore
    awarded_before = django_filters.DateFilter(field_name="awarded", lookup_expr="lte")  # type: ignore
    event = django_filters.ModelChoiceFilter(
        queryset=Event.objects.all(),
        label="Event",
        widget=ModelSelect2Widget(
            data_view="event-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )  # type: ignore

    order_by = django_filters.OrderingFilter(
        fields=(
            "awarded",
            "person__family",
        ),
        field_labels={
            "awarded": "Awarded date",
            "person__family": "Person",
        },
    )  # type: ignore

    class Meta:
        model = Award
        fields = (
            "awarded_after",
            "awarded_before",
            "event",
        )


class WorkshopStaffFilter(AMYFilterSet):
    """Form for this filter is never showed up, instead a custom form
    (.forms.WorkshopStaffForm) is used. So there's no need to specify widgets
    here.
    """

    country = django_filters.MultipleChoiceFilter(
        choices=list(Countries()),
        method="filter_country",
    )  # type: ignore
    continent = ContinentFilter(label="Continent")  # type: ignore
    lessons = django_filters.ModelMultipleChoiceFilter(
        label="Lessons",
        queryset=Lesson.objects.all(),
        conjoined=True,  # `AND`
    )  # type: ignore
    is_instructor = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_instructor",
    )  # type: ignore
    is_trainer = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_trainer",
    )  # type: ignore
    languages = django_filters.ModelMultipleChoiceFilter(
        label="Languages",
        queryset=Language.objects.all(),
        conjoined=True,  # `AND`
    )  # type: ignore
    domains = django_filters.ModelMultipleChoiceFilter(
        label="Knowledge Domains",
        queryset=KnowledgeDomain.objects.all(),
        conjoined=True,  # `AND`
    )  # type: ignore
    gender = django_filters.ChoiceFilter(
        label="Gender",
        choices=Person.GENDER_CHOICES,
    )  # type: ignore
    was_helper = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_helper",
    )  # type: ignore
    was_organizer = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_organizer",
    )  # type: ignore
    is_in_progress_trainee = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_in_progress_trainee",
    )  # type: ignore

    def filter_country(self, qs: QuerySet[Person], n: str, v: Any) -> QuerySet[Person]:
        if v:
            return qs.filter(Q(airport__country__in=v) | Q(country__in=v))
        return qs

    def filter_instructor(self, qs: QuerySet[Person], n: str, v: Any) -> QuerySet[Person]:
        if v:
            return qs.filter(is_instructor__gte=1)  # type: ignore
        return qs

    def filter_trainer(self, qs: QuerySet[Person], n: str, v: Any) -> QuerySet[Person]:
        if v:
            return qs.filter(is_trainer__gte=1)  # type: ignore
        return qs

    def filter_helper(self, qs: QuerySet[Person], n: str, v: Any) -> QuerySet[Person]:
        if v:
            return qs.filter(num_helper__gte=1)  # type: ignore
        return qs

    def filter_organizer(self, qs: QuerySet[Person], n: str, v: Any) -> QuerySet[Person]:
        if v:
            return qs.filter(num_organizer__gte=1)  # type: ignore
        return qs

    def filter_in_progress_trainee(self, qs: QuerySet[Person], n: str, v: Any) -> QuerySet[Person]:
        if v:
            return qs.filter(is_trainee__gte=1)  # type: ignore
        return qs
