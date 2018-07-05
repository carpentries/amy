import re

from dal import autocomplete
import django_filters
from django.db.models import Q
from django.forms import widgets
from django_countries import Countries

from workshops.forms import bootstrap_helper_filter, SIDEBAR_DAL_WIDTH
from workshops.models import (
    Event,
    Organization,
    Person,
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

EMPTY_SELECTION = (None, '---------')


class AllCountriesFilter(django_filters.ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct()
        qs = qs.order_by(self.name).values_list(self.name, flat=True)

        choices = [o for o in qs if o]
        countries = Countries()
        countries.only = choices

        self.extra['choices'] = list(countries)
        self.extra['choices'].insert(0, EMPTY_SELECTION)
        return super().field


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
        self.extra['choices'].insert(0, EMPTY_SELECTION)
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


class AMYFilterSet(django_filters.FilterSet):
    """
    This base class sets FormHelper.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default FormHelper
        self.form.helper = bootstrap_helper_filter


class EventFilter(AMYFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person)
    host = ForeignKeyAllValuesFilter(Organization)
    administrator = ForeignKeyAllValuesFilter(Organization)

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
    state = EventStateFilter(choices=STATUS_CHOICES, label='Status')

    invoice_status = django_filters.ChoiceFilter(
        choices=(EMPTY_SELECTION, ) + Event.INVOICED_CHOICES,
    )

    country = AllCountriesFilter()

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
        order_by = ['-slug', 'slug', 'start', '-start', 'end', '-end']


def filter_active_eventrequest(qs, name, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class EventRequestFilter(AMYFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person)
    country = AllCountriesFilter()
    active = django_filters.ChoiceFilter(
        choices=(('all', 'All'), ('true', 'Open'), ('false', 'Closed')),
        label='Status', method=filter_active_eventrequest,
        widget=widgets.RadioSelect,
    )
    workshop_type = django_filters.ChoiceFilter(
        choices=(('', 'All'), ('swc', 'Software-Carpentry'),
                 ('dc', 'Data-Carpentry')),
        label='Workshop type',
        widget=widgets.RadioSelect,
    )

    class Meta:
        model = EventRequest
        fields = [
            'assigned_to',
            'workshop_type',
            'active',
            'country',
        ]
        order_by = ['-created_at', 'created_at']


class OrganizationFilter(AMYFilterSet):
    country = AllCountriesFilter()

    membership__variant = django_filters.MultipleChoiceFilter(
        label='Memberships (current or past)',
        choices=Membership.MEMBERSHIP_CHOICES,
    )

    class Meta:
        model = Organization
        fields = [
            'country',
        ]
        order_by = ['fullname', '-fullname', 'domain', '-domain', ]


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


class MembershipFilter(AMYFilterSet):
    organization_name = django_filters.CharFilter(
        label='Organization name',
        name='organization__fullname',
        lookup_expr='icontains',
    )

    MEMBERSHIP_CHOICES = (('', 'Any'),) + Membership.MEMBERSHIP_CHOICES
    variant = django_filters.ChoiceFilter(choices=MEMBERSHIP_CHOICES)

    CONTRIBUTION_CHOICES = (('', 'Any'),) + Membership.CONTRIBUTION_CHOICES
    contribution_type = django_filters.ChoiceFilter(choices=CONTRIBUTION_CHOICES)

    class Meta:
        model = Membership
        fields = [
            'organization_name',
            'variant',
            'contribution_type',
        ]


class PersonFilter(AMYFilterSet):
    taught_workshops = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(), label='Taught at workshops of type',
        method=filter_taught_workshops,
    )

    class Meta:
        model = Person
        fields = [
            'badges', 'taught_workshops',
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
        return queryset.filter(Q(swc_eligible=True, is_swc_instructor=False) |
                               Q(dc_eligible=True, is_dc_instructor=False))
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

    class Meta:
        model = Person
        fields = [
            'search',
            'all_persons',
            'homework',
            'is_instructor',
            'training',
        ]
        order_by = ["-last_login", "lastname", "-lastname", "firstname", "-firstname",
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
        else:
            return super().get_order_by(order_value)


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
        name='group_name',
        lookup_expr='icontains',
        label='Group')

    state = django_filters.ChoiceFilter(
        label='State',
        choices=[('no_d', 'Pending or accepted')] + TrainingRequest.STATES,
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
        order_by = ['created_at',
                    '-created_at',
                    'trainee firstname',
                    '-trainee firstname',
                    'trainee lastname',
                    '-trainee lastname']

    def get_order_by(self, order_value):
        if order_value == 'trainee firstname':
            return ['personal', 'family']
        elif order_value == '-trainee firstname':
            return ['-personal', '-family']
        elif order_value == 'trainee lastname':
            return ['family', 'personal']
        elif order_value == '-trainee lastname':
            return ['-family', '-personal']
        else:
            return super().get_order_by(order_value)


class TaskFilter(AMYFilterSet):
    event = django_filters.ModelChoiceFilter(
        queryset=Event.objects.all(),
        label='Event',
        widget=autocomplete.ModelSelect2(
            url='event-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        ),
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
        order_by = [
            ['event__slug', 'Event'],
            ['-event__slug', 'Event (descending)'],
            ['person__family', 'Person'],
            ['-person__family', 'Person (descending)'],
            ['role', 'Role'],
            ['-role', 'Role (descending)'],
        ]


class AirportFilter(AMYFilterSet):
    fullname = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Airport
        fields = [
            'fullname',
        ]
        order_by = ["iata", "-iata", "fullname", "-fullname"]


class BadgeAwardsFilter(AMYFilterSet):
    awarded_after = django_filters.DateFilter(name='awarded',
                                              lookup_expr='gte')
    awarded_before = django_filters.DateFilter(name='awarded',
                                               lookup_expr='lte')

    class Meta:
        model = Award
        fields = (
            'awarded_after', 'awarded_before', 'event',
        )
        order_by = [
            '-awarded', 'awarded', '-person__family',
            'person__family',
        ]


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

    class Meta:
        model = InvoiceRequest
        fields = [
            'status',
            'organization',
        ]
        order_by = [
            '-event__slug', 'event__slug',
            'organization__domain', '-organization__domain',
        ]


def filter_active_eventsubmission(qs, name, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class EventSubmissionFilter(AMYFilterSet):
    active = django_filters.ChoiceFilter(
        choices=(('', 'All'), ('true', 'Open'), ('false', 'Closed')),
        label='Status', method=filter_active_eventsubmission,
        widget=widgets.RadioSelect,
    )
    assigned_to = ForeignKeyAllValuesFilter(Person)

    class Meta:
        model = EventSubmission
        fields = [
            'active',
            'assigned_to',
        ]
        order_by = [
            '-created_at', 'created_at',
        ]


def filter_active_dcselforganizedeventrequest(qs, name, value):
    if value == 'true':
        return qs.filter(active=True)
    elif value == 'false':
        return qs.filter(active=False)
    return qs


class DCSelfOrganizedEventRequestFilter(AMYFilterSet):
    active = django_filters.ChoiceFilter(
        choices=(('', 'All'), ('true', 'Open'), ('false', 'Closed')),
        label='Status', method=filter_active_dcselforganizedeventrequest,
        widget=widgets.RadioSelect,
    )
    assigned_to = ForeignKeyAllValuesFilter(Person)

    class Meta:
        model = DCSelfOrganizedEventRequest
        fields = [
            'active',
            'assigned_to',
        ]
        order_by = [
            '-created_at', 'created_at',
        ]
