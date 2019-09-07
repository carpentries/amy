from collections import OrderedDict
import datetime
from itertools import accumulate

from django.db.models import (
    Case,
    Count,
    F,
    IntegerField,
    Min,
    Prefetch,
    Sum,
    Value,
    When,
)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.metadata import SimpleMetadata
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    IsAuthenticatedOrReadOnly, IsAuthenticated, BasePermission
)
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework_csv.renderers import CSVRenderer
from rest_framework_yaml.renderers import YAMLRenderer

from workshops.models import (
    Badge,
    Airport,
    Event,
    Tag,
    Organization,
    Task,
    Award,
    Person,
    TrainingRequest,
    is_admin,
)
from workshops.util import get_members, default_membership_cutoff, str2bool

from api.serializers import (
    PersonNameEmailUsernameSerializer,
    ExportBadgesSerializer,
    ExportBadgesByPersonSerializer,
    ExportInstructorLocationsSerializer,
    ExportEventSerializer,
    WorkshopsOverTimeSerializer,
    InstructorsOverTimeSerializer,
    InstructorNumTaughtSerializer,
    InstructorsByTimePeriodSerializer,
    OrganizationSerializer,
    EventSerializer,
    TaskSerializer,
    AirportSerializer,
    AwardSerializer,
    PersonSerializer,
    PersonSerializerAllData,
    TrainingRequestWithPersonSerializer,
    TrainingRequestForManualScoringSerializer,
)

from api.filters import (
    EventFilter,
    TaskFilter,
    PersonFilter,
    InstructorsOverTimeFilter,
    WorkshopsOverTimeFilter,
    LearnersOverTimeFilter,
    TrainingRequestFilterIDs,
)

from api.renderers import (
    TrainingRequestCSVRenderer,
    TrainingRequestManualScoreCSVRenderer,
)


class IsAdmin(BasePermission):
    """This permission allows only admin users to view the API content."""
    def has_permission(self, request, view):
        return is_admin(request.user)


class HasRestrictedPermission(BasePermission):
    """This permission allows only users with special
    'can_access_restricted_API' permission."""
    def has_permission(self, request, view):
        return request.user.has_perm('workshops.can_access_restricted_API')


class QueryMetadata(SimpleMetadata):
    """Additionally include info about query parameters."""

    def determine_metadata(self, request, view):
        data = super().determine_metadata(request, view)

        try:
            data['query_params'] = view.get_query_params_description()
        except AttributeError:
            pass

        return data


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response(OrderedDict([
            ('export-badges', reverse('api:export-badges', request=request,
                                      format=format)),
            ('export-badges-by-person', reverse('api:export-badges-by-person',
                                                request=request,
                                                format=format)),
            ('export-instructors', reverse('api:export-instructors',
                                           request=request, format=format)),
            ('export-members', reverse('api:export-members', request=request,
                                       format=format)),
            ('export-person-data', reverse('api:export-person-data',
                                           request=request, format=format)),
            ('events-published', reverse('api:events-published',
                                         request=request, format=format)),
            ('reports-list', reverse('api:reports-list',
                                     request=request, format=format)),
            ('training-requests', reverse('api:training-requests',
                                     request=request, format=format)),

            # "new" API list-type endpoints below
            ('airport-list', reverse('api:airport-list', request=request,
                                     format=format)),
            ('person-list', reverse('api:person-list', request=request,
                                    format=format)),
            ('event-list', reverse('api:event-list', request=request,
                                   format=format)),
            ('organization-list', reverse('api:organization-list',
                                          request=request,
                                          format=format)),
        ]))


class ExportBadgesView(ListAPIView):
    """List all badges and people who have them."""
    permission_classes = (IsAuthenticated, HasRestrictedPermission, )
    paginator = None  # disable pagination

    queryset = Badge.objects.prefetch_related('award_set', 'award_set__person')
    serializer_class = ExportBadgesSerializer


class ExportBadgesByPersonView(ListAPIView):
    """List all badges and people who have them grouped by person."""
    permission_classes = (IsAuthenticated, HasRestrictedPermission, )
    paginator = None  # disable pagination

    queryset = Person.objects.exclude(badges=None).prefetch_related('badges')
    serializer_class = ExportBadgesByPersonSerializer


class ExportInstructorLocationsView(ListAPIView):
    """List all airports and instructors located near them."""
    permission_classes = (IsAuthenticated, HasRestrictedPermission, )
    paginator = None  # disable pagination

    serializer_class = ExportInstructorLocationsSerializer

    metadata_class = QueryMetadata

    def get_queryset(self):
        """This queryset uses a special object `Prefetch` to apply specific
        filters to the Airport.person_set objects; this way we can "filter" on
        Airport.person_set objects - something that wasn't available a few
        years ago... Additionally, there's no way to filter out Airports with
        no instructors."""

        # adjust queryset for the request params
        person_qs = Person.objects.all()

        publish_profile = None
        may_contact = None
        # `self.request` is only available during "real" request-response cycle
        if hasattr(self, 'request'):
            publish_profile = str2bool(
                self.request.query_params.get('publish_profile', None)
            )
            may_contact = str2bool(
                self.request.query_params.get('may_contact', None)
            )

        if publish_profile is not None:
            person_qs = person_qs.filter(publish_profile=publish_profile)
        if may_contact is not None:
            person_qs = person_qs.filter(may_contact=may_contact)

        return (
            Airport.objects
            .exclude(person=None)
            .distinct()
            .prefetch_related(
                Prefetch(
                    'person_set',
                    queryset=person_qs.filter(
                        badges__in=Badge.objects.instructor_badges()
                    ).distinct(),
                    to_attr='public_instructor_set',
                )
            )
        )

    def get_query_params_description(self):
        return {
            'publish_profile': 'Filter on user `publish_profile` bool value.',
            'may_contact': 'Filter on user `may_contact` bool value.',
        }


class ExportMembersView(ListAPIView):
    """Show everyone who qualifies as an SCF member."""
    permission_classes = (IsAuthenticated, IsAdmin, HasRestrictedPermission, )
    paginator = None  # disable pagination

    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [CSVRenderer, ]

    serializer_class = PersonNameEmailUsernameSerializer

    metadata_class = QueryMetadata

    def get_queryset(self):
        earliest_default, latest_default = default_membership_cutoff()

        earliest = self.request.query_params.get('earliest', None)
        if earliest is not None:
            try:
                earliest = datetime.datetime.strptime(earliest, '%Y-%m-%d') \
                                            .date()
            except ValueError:
                earliest = earliest_default
        else:
            earliest = earliest_default

        latest = self.request.query_params.get('latest', None)
        if latest is not None:
            try:
                latest = datetime.datetime.strptime(latest, '%Y-%m-%d').date()
            except ValueError:
                latest = latest_default
        else:
            latest = latest_default

        return get_members(earliest, latest)

    def get_query_params_description(self):
        return {
            'earliest': 'Date of earliest workshop someone taught at.'
                        '  Defaults to -2*365 days from current date.',
            'latest': 'Date of latest workshop someone taught at.'
                      '  Defaults to current date.',
        }


class ExportPersonDataView(RetrieveAPIView):
    permission_classes = (IsAuthenticated, )
    serializer_class = PersonSerializerAllData
    queryset = Person.objects.all()

    def get_object(self):
        """Get logged-in user data, make it impossible to gather someone else's
        data this way."""
        user = self.request.user

        if user.is_anonymous:
            return self.get_queryset().none()
        else:
            return self.get_queryset().get(pk=user.pk)


class PublishedEvents(ListAPIView):
    """List published events."""
    # only events that have both a starting date and a URL
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination
    serializer_class = ExportEventSerializer
    filterset_class = EventFilter
    queryset = Event.objects.published_events().attendance()


class TrainingRequests(ListAPIView):
    permission_classes = (IsAuthenticated, IsAdmin)
    paginator = None
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + \
        [TrainingRequestCSVRenderer, TrainingRequestManualScoreCSVRenderer]
    queryset = (
        TrainingRequest.objects.all()
            .select_related('person')
            .prefetch_related(
                'previous_involvement', 'domains',
                Prefetch('person__award_set',
                    queryset=Award.objects.select_related('badge'),
                ),
                Prefetch('person__task_set',
                    queryset=Task.objects
                        .filter(role__name='learner', event__tags__name='TTT')
                        .select_related('event'),
                    to_attr='training_tasks',
                ),
            )
        )
    filterset_class = TrainingRequestFilterIDs

    def get_serializer_class(self):
        if self.request.query_params.get('manualscore'):
            return TrainingRequestForManualScoringSerializer
        else:
            return TrainingRequestWithPersonSerializer



class ReportsViewSet(ViewSet):
    """This viewset will return data for many of our reports.

    This is implemented as a ViewSet, but actions like create/list/retrieve/etc
    are missing, because we want to still have the power and simplicity of
    a router."""
    permission_classes = (IsAuthenticated, IsAdmin)
    event_queryset = Event.objects.past_events().attendance().order_by('start')
    award_queryset = Award.objects.order_by('awarded')

    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, CSVRenderer,
                        YAMLRenderer)

    # YAML and CSV renderers don't understand generators (>.<) so we had to
    # turn the `accumulate` generator results into a list
    formats_requiring_lists = ('csv', 'yaml')

    def _add_counts(self, a, b):
        c = b
        c['count'] = (a.get('count') or 0) + (b.get('count') or 0)
        return c

    def _only_latest_date(self, iterable):
        it = iter(iterable)
        try:
            prev_ = next(it)
        except StopIteration:
            return
        next_ = None
        for next_ in it:
            if prev_['date'] != next_['date']:
                yield prev_
            prev_ = next_
        if next_ is not None:
            yield next_

    def listify(self, iterable, request, format=None):
        """Some renderers require lists instead of any iterables for rendering.
        This function conditionally turns iterables into lists based on the
        format requested by browser."""
        # choose either '?format=...' or '/url.format' or None
        format_ = (request.query_params.get('format') or format or '').lower()

        if format_ in self.formats_requiring_lists:
            # list-ify the generator for renderers requiring lists
            return list(iterable)

        return iterable

    @action(detail=False, methods=['GET'])
    def workshops_over_time(self, request, format=None):
        """Cumulative number of workshops run by Software Carpentry and other
        carpentries over time."""
        qs = self.event_queryset
        qs = WorkshopsOverTimeFilter(request.GET, queryset=qs).qs
        qs = qs.annotate(count=Count('id'))

        serializer = WorkshopsOverTimeSerializer(qs, many=True)

        # run a cumulative generator over the data
        data = accumulate(serializer.data, self._add_counts)

        data = self.listify(data, request, format)

        return Response(data)

    @action(detail=False, methods=['GET'])
    def learners_over_time(self, request, format=None):
        """Cumulative number of learners attending Software-Carpentry and other
        carpentries' workshops over time."""
        qs = self.event_queryset
        qs = LearnersOverTimeFilter(request.GET, queryset=qs).qs
        qs = qs.annotate(count=Sum('attendance'))

        # we reuse the serializer because it works here too
        serializer = WorkshopsOverTimeSerializer(qs, many=True)

        # run a cumulative generator over the data
        data = accumulate(serializer.data, self._add_counts)

        data = self.listify(data, request, format)

        return Response(data)

    @action(detail=False, methods=['GET'])
    def instructors_over_time(self, request, format=None):
        """Cumulative number of instructor appearances on workshops over
        time."""

        badges = Badge.objects.instructor_badges()

        qs = Person.objects.filter(badges__in=badges).annotate(
            date=Min('award__awarded'),
            count=Value(1, output_field=IntegerField())
        ).order_by('date')

        filter = InstructorsOverTimeFilter(request.GET, queryset=qs)

        serializer = InstructorsOverTimeSerializer(filter.qs, many=True)

        # run a cumulative generator over the data
        data = accumulate(serializer.data, self._add_counts)

        # drop data for the same days by showing the last record for
        # particular date
        data = self._only_latest_date(data)

        data = self.listify(data, request, format)

        return Response(data)

    @action(detail=False, methods=['GET'])
    def instructor_num_taught(self, request, format=None):
        badges = Badge.objects.instructor_badges()
        persons = Person.objects.filter(badges__in=badges).annotate(
            num_taught_SWC=Count(
                Case(
                    When(
                        task__role__name='instructor',
                        task__event__tags__name='SWC',
                        then=F('task'),
                    ),
                ),
                distinct=True
            ),
            num_taught_DC=Count(
                Case(
                    When(
                        task__role__name='instructor',
                        task__event__tags__name='DC',
                        then=F('task'),
                    ),
                ),
                distinct=True
            ),
            num_taught_LC=Count(
                Case(
                    When(
                        task__role__name='instructor',
                        task__event__tags__name='LC',
                        then=F('task'),
                    ),
                ),
                distinct=True
            ),
            num_taught_TTT=Count(
                Case(
                    When(
                        task__role__name='instructor',
                        task__event__tags__name='TTT',
                        then=F('task'),
                    ),
                ),
                distinct=True
            ),
            num_taught_total=Count(
                Case(
                    When(
                        task__role__name='instructor',
                        then=F('task'),
                    ),
                ),
                distinct=True
            ),
        ).order_by('-num_taught_total')
        serializer = InstructorNumTaughtSerializer(
            persons, many=True, context=dict(request=request))
        return Response(serializer.data)

    def _default_start_end_dates(self, start=None, end=None):
        """Parse GET start and end dates or return default values for them."""
        today = datetime.date.today()
        start_of_year = datetime.date(today.year, 1, 1)
        end_of_year = (datetime.date(today.year + 1, 1, 1) -
                       datetime.timedelta(days=1))

        if start is not None:
            try:
                start = datetime.datetime.strptime(start, '%Y-%m-%d').date()
            except ValueError:
                start = start_of_year
        else:
            start = start_of_year

        if end is not None:
            try:
                end = datetime.datetime.strptime(end, '%Y-%m-%d').date()
            except ValueError:
                end = end_of_year
        else:
            end = end_of_year

        return start, end

    @action(detail=False, methods=['GET'])
    def all_activity_over_time(self, request, format=None):
        """Workshops, instructors, and missing data in specific periods."""
        start, end = self._default_start_end_dates(
            start=request.query_params.get('start', None),
            end=request.query_params.get('end', None))

        data = self.get_all_activity_over_time(start, end)
        data['missing']['attendance'] = self.listify(
            data['missing']['attendance'], request, format=format)
        data['missing']['instructors'] = self.listify(
            data['missing']['instructors'], request, format=format)
        return Response(data)

    def get_all_activity_over_time(self, start, end):
        events_qs = Event.objects.filter(start__gte=start, start__lte=end) \
                                 .order_by('-start')
        swc_tag = Tag.objects.get(name='SWC')
        dc_tag = Tag.objects.get(name='DC')
        lc_tag = Tag.objects.get(name='LC')
        wise_tag = Tag.objects.get(name='WiSE')
        TTT_tag = Tag.objects.get(name='TTT')
        self_organized_host = Organization.objects.get(domain='self-organized')

        # count workshops: SWC, DC, LC, total (SWC, DC and LC), self-organized,
        # WiSE, TTT
        swc_workshops = events_qs.filter(tags=swc_tag)
        dc_workshops = events_qs.filter(tags=dc_tag)
        lc_workshops = events_qs.filter(tags=lc_tag)
        total_workshops = events_qs.filter(
            tags__in=[swc_tag, dc_tag, lc_tag]).count()
        wise_workshops = events_qs.filter(tags=wise_tag).count()
        ttt_workshops = events_qs.filter(tags=TTT_tag).count()
        self_organized_workshops = events_qs \
            .filter(administrator=self_organized_host).count()

        # total and unique instructors for SWC, DC, LC workshops
        swc_total_instr = Person.objects \
            .filter(task__event__in=swc_workshops,
                    task__role__name='instructor')
        swc_unique_instr = swc_total_instr.distinct().count()
        swc_total_instr = swc_total_instr.count()

        dc_total_instr = Person.objects \
            .filter(task__event__in=dc_workshops,
                    task__role__name='instructor')
        dc_unique_instr = dc_total_instr.distinct().count()
        dc_total_instr = dc_total_instr.count()

        lc_total_instr = Person.objects \
            .filter(task__event__in=lc_workshops,
                    task__role__name='instructor')
        lc_unique_instr = lc_total_instr.distinct().count()
        lc_total_instr = lc_total_instr.count()

        # total learners for SWC, DC, LC workshops
        swc_total_learners = swc_workshops.attendance().aggregate(
            learners_total=Sum('attendance')
        )['learners_total']
        dc_total_learners = dc_workshops.attendance().aggregate(
            learners_total=Sum('attendance')
        )['learners_total']
        lc_total_learners = lc_workshops.attendance().aggregate(
            learners_total=Sum('attendance')
        )['learners_total']

        # Workshops missing any of this data.
        missing_attendance = events_qs.attendance().filter(attendance=None) \
                                      .values_list('slug', flat=True)
        missing_instructors = events_qs.annotate(
            instructors=Sum(
                Case(
                    When(task__role__name='instructor', then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        ).filter(instructors=0).values_list('slug', flat=True)

        return {
            'start': start,
            'end': end,
            'workshops': {
                'SWC': swc_workshops.count(),
                'DC': dc_workshops.count(),
                'LC': lc_workshops.count(),

                # This dictionary is traversed in a template where we cannot
                # write "{{ data.workshops.SWC,DC }}", because commas are
                # disallowed in templates. Therefore, we include
                # total_workshops under different keys:
                # - 'SWC,DC' and 'SWC_or_DC' - for backward compatibility,
                # - 'carpentries' - new name for SWC/DC/LC collective
                'SWC,DC': total_workshops,
                'SWC_or_DC': total_workshops,
                'carpentries': total_workshops,

                'WiSE': wise_workshops,
                'TTT': ttt_workshops,

                # We include self_organized_workshops twice, under two
                # different keys, for the same reason as total_workshops.
                'self-organized': self_organized_workshops,
                'self_organized': self_organized_workshops,
            },
            'instructors': {
                'SWC': {
                    'total': swc_total_instr,
                    'unique': swc_unique_instr,
                },
                'DC': {
                    'total': dc_total_instr,
                    'unique': dc_unique_instr,
                },
                'LC': {
                    'total': lc_total_instr,
                    'unique': lc_unique_instr,
                },
            },
            'learners': {
                'SWC': swc_total_learners,
                'DC': dc_total_learners,
                'LC': lc_total_learners,
            },
            'missing': {
                'attendance': missing_attendance,
                'instructors': missing_instructors,
            }
        }

    def instructors_by_time_queryset(self, start, end, only_TTT=False,
                                     only_non_TTT=False):
        """Just a queryset to be reused in other view.

        `start` and `end` define a timerange for events.
        `only_TTT` limits output to only TTT events, and
        `only_non_TTT` excludes TTT events from the results."""
        tasks = Task.objects.filter(
            event__start__gte=start,
            event__end__lte=end,
            role__name='instructor',
            person__may_contact=True,
        )

        # include only TTT events
        if only_TTT:
            tags = Tag.objects.filter(name__in=['TTT'])
            tasks = (
                tasks.filter(event__tags__in=tags)
            )

        # exclude TTT events
        elif only_non_TTT:
            tags = Tag.objects.filter(name__in=['TTT'])
            tasks = (
                tasks.exclude(event__tags__in=tags)
            )

        # exclude stalled or unresponsive events
        rejected_tags = Tag.objects.filter(name__in=['stalled',
                                                     'unresponsive'])

        tasks = (
            tasks
            .exclude(event__tags__in=rejected_tags)
            .order_by('event', 'person', 'role')
            .select_related('event', 'person', 'role')
            .prefetch_related('event__tags')
            .annotate(
                num_taught=Sum(
                    Case(
                        When(person__task__role__name='instructor',
                             then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    ),
                )
            )
        )
        return tasks

    @action(detail=False, methods=['GET'])
    def instructors_by_time(self, request, format=None):
        """Workshops and instructors who taught in specific time period."""
        start, end = self._default_start_end_dates(
            start=self.request.query_params.get('start', None),
            end=self.request.query_params.get('end', None))

        mode = self.request.query_params.get('mode', 'all')

        tasks = self.instructors_by_time_queryset(
            start, end,
            only_TTT=(mode == 'TTT'),
            only_non_TTT=(mode == 'nonTTT'),
        )

        serializer = InstructorsByTimePeriodSerializer(
            tasks, many=True, context=dict(request=request))
        return Response(serializer.data)

    def list(self, request, format=None):
        """Display list of links to the reports."""
        return Response({
            'reports-all-activity-over-time': reverse(
                'api:reports-all-activity-over-time', request=request,
                format=format),
            'reports-instructor-num-taught': reverse(
                'api:reports-instructor-num-taught', request=request,
                format=format),
            'reports-instructors-over-time': reverse(
                'api:reports-instructors-over-time', request=request,
                format=format),
            'reports-learners-over-time': reverse(
                'api:reports-learners-over-time', request=request,
                format=format),
            'reports-workshops-over-time': reverse(
                'api:reports-workshops-over-time', request=request,
                format=format),
            'reports-instructors-by-time': reverse(
                'api:reports-instructors-by-time', request=request,
                format=format),
        })


# ----------------------
# "new" API starts below
# ----------------------


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """List many hosts or retrieve only one."""
    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    lookup_field = 'domain'
    lookup_value_regex = r'[^/]+'  # the default one doesn't work with domains
    pagination_class = StandardResultsSetPagination


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """List many events or retrieve only one."""
    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Event.objects \
                            .select_related('host', 'administrator') \
                            .prefetch_related('tags') \
                            .attendance()
    serializer_class = EventSerializer
    lookup_field = 'slug'
    pagination_class = StandardResultsSetPagination
    filterset_class = EventFilter


class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """List tasks belonging to specific event."""
    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TaskSerializer
    pagination_class = StandardResultsSetPagination
    filterset_class = TaskFilter
    _event_slug = None

    def get_queryset(self):
        qs = Task.objects.all().select_related('person', 'role',
                                               'person__airport')
        if self._event_slug:
            qs = qs.filter(event__slug=self._event_slug)
        return qs

    def list(self, request, event_slug=None):
        self._event_slug = event_slug
        return super().list(request)

    def retrieve(self, request, pk=None, event_slug=None):
        self._event_slug = event_slug
        return super().retrieve(request, pk=pk)


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    """List many people or retrieve only one person."""
    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Person.objects.all().select_related('airport') \
                     .prefetch_related('badges', 'domains', 'lessons') \
                     .distinct()
    serializer_class = PersonSerializer
    pagination_class = StandardResultsSetPagination
    filterset_class = PersonFilter


class AwardViewSet(viewsets.ReadOnlyModelViewSet):
    """List awards belonging to specific person."""
    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = AwardSerializer
    _person_pk = None

    def get_queryset(self):
        qs = Award.objects.all()
        if self._person_pk:
            qs = qs.filter(person=self._person_pk)
        return qs

    def list(self, request, person_pk=None):
        self._person_pk = person_pk
        return super().list(request)

    def retrieve(self, request, pk=None, person_pk=None):
        self._person_pk = person_pk
        return super().retrieve(request, pk=pk)


class PersonTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """List tasks done by specific person."""
    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TaskSerializer
    _person_pk = None

    def get_queryset(self):
        qs = Task.objects.all()
        if self._person_pk:
            qs = qs.filter(person=self._person_pk)
        return qs

    def list(self, request, person_pk=None):
        self._person_pk = person_pk
        return super().list(request)

    def retrieve(self, request, pk=None, person_pk=None):
        self._person_pk = person_pk
        return super().retrieve(request, pk=pk)


class AirportViewSet(viewsets.ReadOnlyModelViewSet):
    """List many airports or retrieve only one."""
    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    lookup_field = 'iata__iexact'
    lookup_url_kwarg = 'iata'
    pagination_class = StandardResultsSetPagination
