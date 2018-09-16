from datetime import date
import re

from dal import autocomplete
from dal_select2.widgets import (
    ListSelect2,
    Select2,
    Select2Multiple,
    ModelSelect2Multiple,
)
import django_filters
from django.db.models import Q
from django.forms import widgets
from django_countries import Countries

from workshops.forms import bootstrap_helper_filter, SIDEBAR_DAL_WIDTH
from workshops.models import (
    StateMixin,
    Event,
    Organization,
    Person,
    Badge,
    Airport,
    EventRequest,
    Tag,
    Task,
    Award,
    InvoiceRequest,
    EventSubmission,
    DCSelfOrganizedEventRequest,
    TrainingRequest,
    Membership,
)


class AllCountriesFilter(django_filters.ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct()
        qs = qs.order_by(self.field_name).values_list(self.field_name,
                                                      flat=True)

        choices = [o for o in qs if o]
        countries = Countries()
        countries.only = choices

        self.extra['choices'] = list(countries)
        return super().field


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
        self.extra['choices'] = [(o.pk, str(o)) for o in qs2]
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


class NamesOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra['choices'] += [
            ('lastname', 'Last name'),
            ('-lastname', 'Last name (descending)'),
            ('firstname', 'First name'),
            ('-firstname', 'First name (descending)'),
        ]

    def filter(self, qs, value):
        ordering = super().filter(qs, value)

        if not value:
            return ordering

        # `value` is a list
        if any(v in ['lastname'] for v in value):
            return ordering.order_by('family', 'middle', 'personal')
        elif any(v in ['-lastname'] for v in value):
            return ordering.order_by('-family', '-middle', '-personal')
        elif any(v in ['firstname'] for v in value):
            return ordering.order_by('personal', 'middle', 'family')
        elif any(v in ['-firstname'] for v in value):
            return ordering.order_by('-personal', '-middle', '-family')

        return ordering


#------------------------------------------------------------


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
        label='State',
        widget=widgets.RadioSelect,
        empty_label='Any',
        null_label=None,
        null_value=None,
    )


#------------------------------------------------------------


class EventFilter(AMYFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2())
    host = ForeignKeyAllValuesFilter(Organization, widget=Select2())
    administrator = ForeignKeyAllValuesFilter(Organization, widget=Select2())

    STATUS_CHOICES = [
        ('', 'All'),
        ('active', 'Active'),
        ('past_events', 'Past'),
        ('ongoing_events', 'Ongoing'),
        ('upcoming_events', 'Upcoming'),
        ('unpublished_events', 'Unpublished'),
        ('published_events', 'Published'),
        ('uninvoiced_events', 'Uninvoiced'),
        ('metadata_changed', 'Detected changes in metadata'),
    ]
    state = EventStateFilter(choices=STATUS_CHOICES, label='Status',
                             widget=Select2())

    invoice_status = django_filters.ChoiceFilter(
        choices=Event.INVOICED_CHOICES,
    )

    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(), label='Tags',
        widget=ModelSelect2Multiple(),
    )

    country = AllCountriesFilter(widget=Select2())

    order_by = django_filters.OrderingFilter(
        fields=(
            'slug',
            'start',
            'end',
        ),
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
            'country',
        ]


def filter_active_eventrequest(qs, name, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class EventRequestFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2())
    country = AllCountriesFilter(widget=Select2())
    workshop_type = django_filters.ChoiceFilter(
        choices=(('swc', 'Software-Carpentry'),
                 ('dc', 'Data-Carpentry')),
        label='Workshop type',
        empty_label='All',
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            'created_at',
        ),
    )

    class Meta:
        model = EventRequest
        fields = [
            'state',
            'assigned_to',
            'workshop_type',
            'country',
        ]


class OrganizationFilter(AMYFilterSet):
    country = AllCountriesFilter(widget=Select2())

    membership__variant = django_filters.MultipleChoiceFilter(
        label='Memberships (current or past)',
        choices=Membership.MEMBERSHIP_CHOICES,
        widget=Select2Multiple(),
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            'fullname',
            'domain',
        ),
    )

    class Meta:
        model = Organization
        fields = [
            'country',
        ]


def filter_training_seats_only(queryset, name, active):
    """Limit Memberships to only active entries."""
    if active:
        today = date.today()
        return queryset.filter(agreement_start__gte=today,
                               agreement_end__lte=today)
    else:
        return queryset

def filter_training_seats_only(queryset, name, seats):
    """Limit Memberships to only entries with some training seats allowed."""
    if seats:
        return queryset.filter(instructor_training_seats_total__gt=0)
    else:
        return queryset


def filter_nonpositive_remaining_seats(queryset, name, seats):
    """Limit Memberships to only entries with negative remaining seats."""
    if seats:
        return queryset.filter(instructor_training_seats_remaining__lt=0)
    else:
        return queryset


class MembershipFilter(AMYFilterSet):
    organization_name = django_filters.CharFilter(
        label='Organization name',
        field_name='organization__fullname',
        lookup_expr='icontains',
    )

    MEMBERSHIP_CHOICES = (('', 'Any'),) + Membership.MEMBERSHIP_CHOICES
    variant = django_filters.ChoiceFilter(choices=MEMBERSHIP_CHOICES)

    CONTRIBUTION_CHOICES = (('', 'Any'),) + Membership.CONTRIBUTION_CHOICES
    contribution_type = django_filters.ChoiceFilter(choices=CONTRIBUTION_CHOICES)

    active_only = django_filters.BooleanFilter(
        label='Only show active memberships',
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput)

    training_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with non-zero allowed training seats',
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput)

    nonpositive_remaining_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with zero or less remaining seats',
        method=filter_nonpositive_remaining_seats,
        widget=widgets.CheckboxInput)

    order_by = django_filters.OrderingFilter(
        fields=(
            'organization__fullname',
            'organization__domain',
            'agreement_start',
            'agreement_end',
            'instructor_training_seats_remaining',
        ),
    )

    class Meta:
        model = Membership
        fields = [
            'organization_name',
            'variant',
            'contribution_type',
        ]


class MembershipTrainingsFilter(AMYFilterSet):
    organization_name = django_filters.CharFilter(
        label='Organization name',
        field_name='organization__fullname',
        lookup_expr='icontains',
    )

    active_only = django_filters.BooleanFilter(
        label='Only show active memberships',
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput)

    training_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with non-zero allowed training seats',
        method=filter_training_seats_only,
        widget=widgets.CheckboxInput)

    nonpositive_remaining_seats_only = django_filters.BooleanFilter(
        label='Only show memberships with zero or less remaining seats',
        method=filter_nonpositive_remaining_seats,
        widget=widgets.CheckboxInput)

    order_by = django_filters.OrderingFilter(
        fields=(
            'organization__fullname',
            'organization__domain',
            'agreement_start',
            'agreement_end',
            'instructor_training_seats_total',
            'instructor_training_seats_utilized',
            'instructor_training_seats_remaining',
        ),
    )

    class Meta:
        model = Membership
        fields = [
            'organization_name',
        ]


def filter_taught_workshops(queryset, name, values):
    """Limit Persons to only instructors from events with specific tags.

    This needs to be in a separate function because django-filters doesn't
    support `action` parameter as supposed, ie. with
    `method='filter_taught_workshops'` it doesn't call the method; instead it
    tries calling a string, which results in error."""

    if not values:
        return queryset

    return queryset.filter(task__role__name='instructor',
                           task__event__tags__in=values) \
                   .distinct()


class PersonFilter(AMYFilterSet):
    badges = django_filters.ModelMultipleChoiceFilter(
        queryset=Badge.objects.all(), label='Badges',
        widget=ModelSelect2Multiple(),
    )
    taught_workshops = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(), label='Taught at workshops of type',
        method=filter_taught_workshops,
        widget=ModelSelect2Multiple(),
    )

    order_by = NamesOrderingFilter(
        fields=(
            'email',
        ),
    )

    class Meta:
        model = Person
        fields = [
            'badges', 'taught_workshops',
        ]


def filter_all_persons(queryset, name, all_persons):
    """Filter only trainees when all_persons==False."""
    if all_persons:
        return queryset
    else:
        return queryset.filter(
            task__role__name='learner',
            task__event__tags__name='TTT').distinct()


def filter_trainees_by_trainee_name_or_email(queryset, name, value):
    if value:
        # 'Harry Potter' -> ['Harry', 'Potter']
        tokens = re.split('\s+', value)
        # Each token must match email address or github username or personal or
        # family name.
        for token in tokens:
            queryset = queryset.filter(Q(personal__icontains=token) |
                                       Q(family__icontains=token) |
                                       Q(email__icontains=token))
        return queryset
    else:
        return queryset


def filter_trainees_by_unevaluated_homework_presence(queryset, name, flag):
    if flag:  # return only trainees with an unevaluated homework
        return queryset.filter(trainingprogress__state='n').distinct()
    else:
        return queryset


def filter_trainees_by_training_request_presence(queryset, name, flag):
    if flag is None:
        return queryset
    elif flag is True:  # return only trainees who submitted training request
        return queryset.filter(trainingrequest__isnull=False).distinct()
    else:  # return only trainees who did not submit training request
        return queryset.filter(trainingrequest__isnull=True)


def filter_trainees_by_instructor_status(queryset, name, choice):
    if choice == '':
        return queryset
    elif choice == 'swc-and-dc':
        return queryset.filter(is_swc_instructor=True, is_dc_instructor=True)
    elif choice == 'swc-or-dc':
        return queryset.filter(Q(is_swc_instructor=True) |
                               Q(is_dc_instructor=True))
    elif choice == 'swc':
        return queryset.filter(is_swc_instructor=True)
    elif choice == 'dc':
        return queryset.filter(is_dc_instructor=True)
    elif choice == 'eligible':
        # Instructor eligible but without any badge.
        # This code is kept in Q()-expressions to allow for fast condition
        # change.
        return queryset.filter(
            Q(instructor_eligible=True) &
            (Q(is_swc_instructor=False) & Q(is_dc_instructor=False))
        )
    else:  # choice == 'no'
        return queryset.filter(is_swc_instructor=False, is_dc_instructor=False)


def filter_trainees_by_training(queryset, name, training):
    if training is None:
        return queryset
    else:
        return queryset.filter(task__role__name='learner',
                               task__event=training).distinct()


class TraineeFilter(AMYFilterSet):
    search = django_filters.CharFilter(
        method=filter_trainees_by_trainee_name_or_email,
        label='Name or Email')

    all_persons = django_filters.BooleanFilter(
        label='Include all people, not only trainees',
        method=filter_all_persons,
        widget=widgets.CheckboxInput)

    homework = django_filters.BooleanFilter(
        label='Only trainees with unevaluated homework',
        widget=widgets.CheckboxInput,
        method=filter_trainees_by_unevaluated_homework_presence,
    )

    training_request = django_filters.BooleanFilter(
        label='Is training request present?',
        method=filter_trainees_by_training_request_presence,
    )

    is_instructor = django_filters.ChoiceFilter(
        label='Is SWC/DC instructor?',
        method=filter_trainees_by_instructor_status,
        choices=[
            ('', 'Unknown'),
            ('swc-and-dc', 'Both SWC and DC'),
            ('swc-or-dc', 'SWC or DC '),
            ('swc', 'SWC instructor'),
            ('dc', 'DC instructor'),
            ('eligible', 'No, but eligible to be certified'),
            ('no', 'No'),
        ]
    )

    training = django_filters.ModelChoiceFilter(
        queryset=Event.objects.ttt(),
        method=filter_trainees_by_training,
        label='Training',
        widget=autocomplete.ModelSelect2(
            url='ttt-event-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        ),
    )

    order_by = NamesOrderingFilter(
        fields=(
            'last_login',
            'email',
        ),
    )

    class Meta:
        model = Person
        fields = [
            'search',
            'all_persons',
            'homework',
            'is_instructor',
            'training',
        ]


def filter_matched(queryset, name, choice):
    if choice == '':
        return queryset
    elif choice == 'u':  # unmatched
        return queryset.filter(person=None)
    elif choice == 'p':  # matched trainee, unmatched training
        return queryset.filter(person__isnull=False)\
                       .exclude(person__task__role__name='learner',
                                person__task__event__tags__name='TTT')\
                       .distinct()
    else:  # choice == 't' <==> matched trainee and training
        return queryset.filter(person__task__role__name='learner',
                               person__task__event__tags__name='TTT')\
                       .distinct()


def filter_by_person(queryset, name, value):
    if value == '':
        return queryset
    else:
        # 'Harry Potter' -> ['Harry', 'Potter']
        tokens = re.split('\s+', value)
        # Each token must match email address or github username or personal or
        # family name.
        for token in tokens:
            queryset = queryset.filter(
                Q(personal__icontains=token) |
                Q(middle__icontains=token) |
                Q(family__icontains=token) |
                Q(email__icontains=token) |
                Q(person__personal__icontains=token) |
                Q(person__middle__icontains=token) |
                Q(person__family__icontains=token) |
                Q(person__email__icontains=token)
            )
        return queryset


def filter_affiliation(queryset, name, affiliation):
    if affiliation == '':
        return queryset
    else:
        return queryset.filter(Q(affiliation__icontains=affiliation) |
                               Q(person__affiliation__icontains=affiliation)) \
                       .distinct()


def filter_training_requests_by_state(queryset, name, choice):
    if choice == 'no_d':
        return queryset.exclude(state='d')
    else:
        return queryset.filter(state=choice)


class TrainingRequestFilter(AMYFilterSet):
    search = django_filters.CharFilter(
        label='Name or Email',
        method=filter_by_person,
    )

    group_name = django_filters.CharFilter(
        field_name='group_name',
        lookup_expr='icontains',
        label='Group')

    state = django_filters.ChoiceFilter(
        label='State',
        choices=(('no_d', 'Pending or accepted'),) + TrainingRequest.STATE_CHOICES,
        method=filter_training_requests_by_state,
    )

    matched = django_filters.ChoiceFilter(
        label='Is Matched?',
        choices=(
            ('', 'Unknown'),
            ('u', 'Unmatched'),
            ('p', 'Matched trainee, unmatched training'),
            ('t', 'Matched trainee and training'),
        ),
        method=filter_matched,
    )

    affiliation = django_filters.CharFilter(
        method=filter_affiliation,
    )

    location = django_filters.CharFilter(lookup_expr='icontains')

    order_by = NamesOrderingFilter(
        fields=(
            'created_at',
        ),
    )

    class Meta:
        model = TrainingRequest
        fields = [
            'search',
            'group_name',
            'state',
            'matched',
            'affiliation',
            'location',
        ]


class TaskFilter(AMYFilterSet):
    event = django_filters.ModelChoiceFilter(
        queryset=Event.objects.all(),
        label='Event',
        widget=autocomplete.ModelSelect2(
            url='event-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        ),
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            ('event__slug', 'event'),
            ('person__family', 'person'),
            ('role', 'role'),
        ),
        field_labels={
            'event__slug': 'Event',
            'person__family': 'Person',
            'role': 'Role',
        }
    )

    class Meta:
        model = Task
        fields = [
            'event',
            # can't filter on person because person's name contains 3 fields:
            # person.personal, person.middle, person.family
            # 'person',
            'role',
        ]


class AirportFilter(AMYFilterSet):
    fullname = django_filters.CharFilter(lookup_expr='icontains')

    order_by = django_filters.OrderingFilter(
        fields=(
            'iata',
            'fullname',
        ),
        field_labels={
            'iata': 'IATA',
            'fullname': 'Full name',
        }
    )

    class Meta:
        model = Airport
        fields = [
            'fullname',
        ]


class BadgeAwardsFilter(AMYFilterSet):
    awarded_after = django_filters.DateFilter(field_name='awarded',
                                              lookup_expr='gte')
    awarded_before = django_filters.DateFilter(field_name='awarded',
                                               lookup_expr='lte')
    event = django_filters.ModelChoiceFilter(
        queryset=Event.objects.all(),
        label='Event',
        widget=autocomplete.ModelSelect2(
            url='event-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        ),
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            'awarded',
            'person__family',
        ),
        field_labels={
            'awarded': 'Awarded date',
            'person__family': 'Person',
        }
    )

    class Meta:
        model = Award
        fields = (
            'awarded_after', 'awarded_before', 'event',
        )


class InvoiceRequestFilter(AMYFilterSet):
    STATUS_CHOICES = (('', 'All'),) + InvoiceRequest.STATUS_CHOICES
    status = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES,
    )

    organization = django_filters.ModelChoiceFilter(
        queryset=Organization.objects.all(),
        label='Organization',
        widget=autocomplete.ModelSelect2(
            url='organization-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        ),
    )

    order_by = django_filters.OrderingFilter(
        fields=(
            'event__slug',
            'organization__domain',
        ),
    )

    class Meta:
        model = InvoiceRequest
        fields = [
            'status',
            'organization',
        ]


def filter_active_eventsubmission(qs, name, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class EventSubmissionFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2())

    order_by = django_filters.OrderingFilter(
        fields=(
            'created_at',
        ),
    )

    class Meta:
        model = EventSubmission
        fields = [
            'state',
            'assigned_to',
        ]


def filter_active_dcselforganizedeventrequest(qs, name, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class DCSelfOrganizedEventRequestFilter(AMYFilterSet, StateFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2())

    order_by = django_filters.OrderingFilter(
        fields=(
            'created_at',
        ),
    )

    class Meta:
        model = DCSelfOrganizedEventRequest
        fields = [
            'state',
            'assigned_to',
        ]
        order_by = [
            '-created_at', 'created_at',
        ]
