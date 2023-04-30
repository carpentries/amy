from typing import Any, Sequence, Union

from django.conf import settings
from django.db.models import Q
from django.forms import widgets
from django_countries import Countries
import django_filters

from dashboard.models import Continent
from workshops.fields import (
    ModelSelect2MultipleWidget,
    ModelSelect2Widget,
    Select2Widget,
)
from workshops.forms import SELECT2_SIDEBAR, bootstrap_helper_filter
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
    StateMixin,
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
    def __init__(self, *args, **kwargs):
        self.extend_countries = kwargs.pop("extend_countries", True)
        super().__init__(*args, **kwargs)

    def _get_countries(self):
        qs = self.model._default_manager.distinct()  # type: ignore
        qs = qs.order_by(self.field_name).values_list(self.field_name, flat=True)
        choices = [o for o in qs if o]
        return choices

    @property
    def field(self):
        choices = self._get_countries()
        if self.extend_countries:
            only = extend_country_choices(choices, settings.COUNTRIES_OVERRIDE)
        else:
            only = {
                abbrv: name
                for abbrv, name in Countries().countries.items()
                if abbrv in choices
            }

        countries = Countries()
        countries.only = only  # type: ignore
        self.extra["choices"] = list(countries)
        return super().field


class AllCountriesFilter(BaseCountriesFilter, django_filters.ChoiceFilter):
    pass


class AllCountriesMultipleFilter(
    BaseCountriesFilter, django_filters.MultipleChoiceFilter
):
    pass


class ForeignKeyAllValuesFilter(django_filters.ChoiceFilter):
    def __init__(self, model, *args, **kwargs):
        self.lookup_model = model
        super().__init__(*args, **kwargs)

    @property
    def field(self):
        name = self.field_name
        model = self.lookup_model

        qs1 = self.model._default_manager.distinct()
        qs1 = qs1.order_by(name).values_list(name, flat=True)
        qs2 = model.objects.filter(pk__in=qs1)
        self.extra["choices"] = [(o.pk, str(o)) for o in qs2]
        return super().field


class EventStateFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if isinstance(value, django_filters.fields.Lookup):
            value = value.value

        # no filtering
        if value in ([], (), {}, None, "", "all"):
            return qs

        # no need to check if value exists in self.extra['choices'] because
        # validation is done by django_filters
        try:
            return getattr(qs, value)()
        except AttributeError:
            return qs


class NamesOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra["choices"] += [
            ("lastname", "Last name"),
            ("-lastname", "Last name (descending)"),
            ("firstname", "First name"),
            ("-firstname", "First name (descending)"),
        ]

    def filter(self, qs, value: list | None):
        if not value:
            return super().filter(qs, value)
        elif any(v in ["lastname"] for v in value):
            return super().filter(qs, ("family", "middle", "personal"))
        elif any(v in ["-lastname"] for v in value):
            return super().filter(qs, ("-family", "-middle", "-personal"))
        elif any(v in ["firstname"] for v in value):
            return super().filter(qs, ("personal", "middle", "family"))
        elif any(v in ["-firstname"] for v in value):
            return super().filter(qs, ("-personal", "-middle", "-family"))
        else:
            return super().filter(qs, value)


class ContinentFilter(django_filters.ChoiceFilter):
    @property
    def field(self):
        self.extra["choices"] = Continent.objects.values_list("pk", "name")
        return super().field

    def filter(self, qs, value):
        if isinstance(value, django_filters.fields.Lookup):
            value = value.value

        # no filtering
        if value in ([], (), {}, None, "", "all"):
            return qs

        # filtering: qs `country` must be in the list of countries given by
        # selected continent
        return qs.filter(country__in=Continent.objects.get(pk=value).countries)


# ------------------------------------------------------------


class AMYFilterSet(django_filters.FilterSet):
    """
    This base class sets FormHelper.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default FormHelper
        self.form.helper = bootstrap_helper_filter


class StateFilterSet(django_filters.FilterSet):
    """A mixin for extending filter classes for Django models that make use of
    `StateMixin`."""

    state = django_filters.ChoiceFilter(
        choices=StateMixin.STATE_CHOICES,
        label="State",
        widget=widgets.RadioSelect,
        empty_label="Any",
        null_label=None,
        null_value=None,
    )


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
    state = EventStateFilter(
        choices=STATUS_CHOICES, label="Status", widget=Select2Widget
    )

    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label="Tags",
        widget=ModelSelect2MultipleWidget(
            data_view="tag-lookup",
        ),
    )

    country = AllCountriesFilter(widget=Select2Widget)
    continent = ContinentFilter(widget=Select2Widget, label="Continent")

    order_by = django_filters.OrderingFilter(
        fields=(
            "slug",
            "start",
            "end",
        ),
    )

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


def filter_taught_workshops(queryset, name, values):
    """Limit Persons to only instructors from events with specific tags.

    This needs to be in a separate function because django-filters doesn't
    support `action` parameter as supposed, ie. with
    `method='filter_taught_workshops'` it doesn't call the method; instead it
    tries calling a string, which results in error."""

    if not values:
        return queryset

    return queryset.filter(
        task__role__name="instructor", task__event__tags__in=values
    ).distinct()


class PersonFilter(AMYFilterSet):
    badges = django_filters.ModelMultipleChoiceFilter(
        queryset=Badge.objects.all(),
        label="Badges",
        widget=ModelSelect2MultipleWidget(
            data_view="badge-lookup",
        ),
    )
    taught_workshops = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        label="Taught at workshops of type",
        method=filter_taught_workshops,
        widget=ModelSelect2MultipleWidget(
            data_view="tag-lookup",
        ),
    )

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
    )

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
    )

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
    fullname = django_filters.CharFilter(lookup_expr="icontains")

    continent = ContinentFilter(widget=Select2Widget, label="Continent")

    order_by = django_filters.OrderingFilter(
        fields=(
            "iata",
            "fullname",
        ),
        field_labels={
            "iata": "IATA",
            "fullname": "Full name",
        },
    )

    class Meta:
        model = Airport
        fields = [
            "fullname",
        ]


class BadgeAwardsFilter(AMYFilterSet):
    awarded_after = django_filters.DateFilter(field_name="awarded", lookup_expr="gte")
    awarded_before = django_filters.DateFilter(field_name="awarded", lookup_expr="lte")
    event = django_filters.ModelChoiceFilter(
        queryset=Event.objects.all(),
        label="Event",
        widget=ModelSelect2Widget(
            data_view="event-lookup",
            attrs=SELECT2_SIDEBAR,
        ),
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            "awarded",
            "person__family",
        ),
        field_labels={
            "awarded": "Awarded date",
            "person__family": "Person",
        },
    )

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
    )
    continent = ContinentFilter(label="Continent")
    lessons = django_filters.ModelMultipleChoiceFilter(
        label="Lessons",
        queryset=Lesson.objects.all(),
        conjoined=True,  # `AND`
    )
    is_instructor = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_instructor",
    )
    is_trainer = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_trainer",
    )
    languages = django_filters.ModelMultipleChoiceFilter(
        label="Languages",
        queryset=Language.objects.all(),
        conjoined=True,  # `AND`
    )
    domains = django_filters.ModelMultipleChoiceFilter(
        label="Knowledge Domains",
        queryset=KnowledgeDomain.objects.all(),
        conjoined=True,  # `AND`
    )
    gender = django_filters.ChoiceFilter(
        label="Gender",
        choices=Person.GENDER_CHOICES,
    )
    was_helper = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_helper",
    )
    was_organizer = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_organizer",
    )
    is_in_progress_trainee = django_filters.BooleanFilter(
        widget=widgets.CheckboxInput,
        method="filter_in_progress_trainee",
    )

    def filter_country(self, qs, n, v):
        if v:
            return qs.filter(Q(airport__country__in=v) | Q(country__in=v))
        return qs

    def filter_instructor(self, qs, n, v):
        if v:
            return qs.filter(is_instructor__gte=1)
        return qs

    def filter_trainer(self, qs, n, v):
        if v:
            return qs.filter(is_trainer__gte=1)
        return qs

    def filter_helper(self, qs, n, v):
        if v:
            return qs.filter(num_helper__gte=1)
        return qs

    def filter_organizer(self, qs, n, v):
        if v:
            return qs.filter(num_organizer__gte=1)
        return qs

    def filter_in_progress_trainee(self, qs, n, v):
        if v:
            return qs.filter(is_trainee__gte=1)
        return qs
