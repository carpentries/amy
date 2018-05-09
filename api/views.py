import datetime
from itertools import accumulate

from django.db.models import Count, Sum, Case, F, When, Value, IntegerField, Min
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.filters import DjangoFilterBackend
from rest_framework.generics import ListAPIView
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
    TodoItem,
    Tag,
    Organization,
    Task,
    Award,
    Person,
    is_admin,
)
from workshops.util import get_members, default_membership_cutoff

from .serializers import (
    PersonNameEmailUsernameSerializer,
    ExportBadgesSerializer,
    ExportBadgesByPersonSerializer,
    ExportInstructorLocationsSerializer,
    ExportEventSerializer,
    TimelineTodoSerializer,
    WorkshopsOverTimeSerializer,
    InstructorsOverTimeSerializer,
    InstructorNumTaughtSerializer,
    InstructorsByTimePeriodSerializer,
    OrganizationSerializer,
    EventSerializer,
    TaskSerializer,
    TodoSerializer,
    AirportSerializer,
    AwardSerializer,
    PersonSerializer,
)

from .filters import (
    EventFilter,
    TaskFilter,
    PersonFilter,
    InstructorsOverTimeFilter,
    WorkshopsOverTimeFilter,
    LearnersOverTimeFilter,
)


class IsAdmin(BasePermission):
    """This permission allows only admin users to view the API content."""
    def has_permission(self, request, view):
        return is_admin(request.user)


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
        return Response({
            'export-badges': reverse('api:export-badges', request=request,
                                     format=format),
            'export-badges-by-person': reverse('api:export-badges-by-person',
                                               request=request,
                                               format=format),
            'export-instructors': reverse('api:export-instructors',
                                          request=request, format=format),
            'export-members': reverse('api:export-members', request=request,
                                      format=format),
            'events-published': reverse('api:events-published',
                                        request=request, format=format),
            'user-todos': reverse('api:user-todos',
                                  request=request, format=format),
            'reports-list': reverse('api:reports-list',
                                    request=request, format=format),

            # "new" API list-type endpoints below
            'airport-list': reverse('api:airport-list', request=request,
                                    format=format),
            'person-list': reverse('api:person-list', request=request,
                                   format=format),
            'event-list': reverse('api:event-list', request=request,
                                  format=format),
            'organization-list': reverse('api:organization-list', request=request,
                                 format=format),
        })


class ExportBadgesView(ListAPIView):
    """List all badges and people who have them."""
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    queryset = Badge.objects.prefetch_related('award_set', 'award_set__person')
    serializer_class = ExportBadgesSerializer


class ExportBadgesByPersonView(ListAPIView):
    """List all badges and people who have them grouped by person."""
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    queryset = Person.objects.exclude(badges=None).prefetch_related('badges')
    serializer_class = ExportBadgesByPersonSerializer


class ExportInstructorLocationsView(ListAPIView):
    """List all airports and instructors located near them."""
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    queryset = Airport.objects.exclude(person=None) \
                              .prefetch_related('person_set')
    serializer_class = ExportInstructorLocationsSerializer


class ExportMembersView(ListAPIView):
    """Show everyone who qualifies as an SCF member."""
    permission_classes = (IsAuthenticated, IsAdmin)
    paginator = None  # disable pagination

    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [CSVRenderer, ]

    serializer_class = PersonNameEmailUsernameSerializer

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


class PublishedEvents(ListAPIView):
    """List published events."""

    # only events that have both a starting date and a URL
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    serializer_class = ExportEventSerializer

    metadata_class = QueryMetadata

    def get_queryset(self):
        """Optionally restrict the returned event set to events hosted by
        specific host or administered by specific admin."""
        queryset = Event.objects.published_events()

        administrator = self.request.query_params.get('administrator', None)
        if administrator is not None:
            queryset = queryset.filter(administrator__pk=administrator)

        host = self.request.query_params.get('host', None)
        if host is not None:
            queryset = queryset.filter(host__pk=host)

        tags = self.request.query_params.getlist('tag', None)
        if tags:
            tags = Tag.objects.filter(name__in=tags)
            for tag in tags:
                queryset = queryset.filter(tags=tag)

        return queryset

    def get_query_params_description(self):
        return {
            'administrator': 'ID of the organization responsible for admin '
                             'work on events.',
            'host': 'ID of the organization hosting the event.',
            'tag': "Events' tag(s). You can use this parameter multiple "
                   "times.",
        }


class UserTodoItems(ListAPIView):
    permission_classes = (IsAuthenticated, IsAdmin)
    paginator = None
    serializer_class = TimelineTodoSerializer

    def get_queryset(self):
        """Return current TODOs for currently logged in user."""
        return TodoItem.objects.user(self.request.user) \
                               .incomplete() \
                               .exclude(due=None) \
                               .select_related('event')


class ReportsViewSet(ViewSet):
    """This viewset will return data for many of our reports.

    This is implemented as a ViewSet, but actions like create/list/retrieve/etc
    are missing, because we want to still have the power and simplicity of
    a router."""
    permission_classes = (IsAuthenticated, IsAdmin)
    event_queryset = Event.objects.past_events().order_by('start')
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

    @list_route(methods=['GET'])
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

    @list_route(methods=['GET'])
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

    @list_route(methods=['GET'])
    def instructors_over_time(self, request, format=None):
        """Cumulative number of instructor appearances on workshops over
        time."""

        badges = Badge.objects.instructor_badges()

        qs = Person.objects.filter(badges__in=badges)
        filter = InstructorsOverTimeFilter(request.GET, queryset=qs)
        qs = filter.qs.annotate(
            date=Min('award__awarded'),
            count=Value(1, output_field=IntegerField())
        ).order_by('date')

        serializer = InstructorsOverTimeSerializer(qs, many=True)

        # run a cumulative generator over the data
        data = accumulate(serializer.data, self._add_counts)

        # drop data for the same days by showing the last record for
        # particular date
        data = self._only_latest_date(data)

        data = self.listify(data, request, format)

        return Response(data)

    @list_route(methods=['GET'])
    def instructor_num_taught(self, request, format=None):
        badges = Badge.objects.instructor_badges()
        persons = Person.objects.filter(badges__in=badges).annotate(
            num_taught=Count(
                Case(
                    When(
                        task__role__name='instructor',
                        then=F('task'),
                    ),
                ),
                distinct=True
            )
        ).order_by('-num_taught')
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

    @list_route(methods=['GET'])
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
        events_qs = Event.objects.filter(start__gte=start, start__lte=end)
        swc_tag = Tag.objects.get(name='SWC')
        dc_tag = Tag.objects.get(name='DC')
        wise_tag = Tag.objects.get(name='WiSE')
        TTT_tag = Tag.objects.get(name='TTT')
        self_organized_host = Organization.objects.get(domain='self-organized')

        # count workshops: SWC, DC, total (SWC and/or DC), self-organized,
        # WiSE, TTT
        swc_workshops = events_qs.filter(tags=swc_tag)
        dc_workshops = events_qs.filter(tags=dc_tag)
        swc_dc_workshops = events_qs.filter(tags__in=[swc_tag, dc_tag]).count()
        wise_workshops = events_qs.filter(tags=wise_tag).count()
        ttt_workshops = events_qs.filter(tags=TTT_tag).count()
        self_organized_workshops = events_qs \
            .filter(administrator=self_organized_host).count()

        # total and unique instructors for both SWC and DC workshops
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

        # total learners for both SWC and DC workshops
        swc_total_learners = swc_workshops.aggregate(count=Sum('attendance'))
        swc_total_learners = swc_total_learners['count']
        dc_total_learners = dc_workshops.aggregate(count=Sum('attendance'))
        dc_total_learners = dc_total_learners['count']

        # Workshops missing any of this data.
        missing_attendance = events_qs.filter(attendance=None) \
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
                # This dictionary is traversed in a template where we cannot
                # write "{{ data.workshops.SWC,DC }}", because commas are
                # disallowed in templates. Therefore, we include
                # swc_dc_workshops twice, under two different keys:
                # - 'SWC,DC' - for backward compatibility,
                # - 'SWC_or_DC' - so that you can access it in a template.
                'SWC,DC': swc_dc_workshops,
                'SWC_or_DC': swc_dc_workshops,
                'WiSE': wise_workshops,
                'TTT': ttt_workshops,
                # We include self_organized_workshops twice, under two
                # different keys, for the same reason as swc_dc_workshops.
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
            },
            'learners': {
                'SWC': swc_total_learners,
                'DC': dc_total_learners,
            },
            'missing': {
                'attendance': missing_attendance,
                'instructors': missing_instructors,
            }
        }

    def instructors_by_time_queryset(self, start, end):
        """Just a queryset to be reused in other view."""
        tags = Tag.objects.filter(name__in=['stalled', 'unresponsive'])
        tasks = Task.objects.filter(
            event__start__gte=start,
            event__end__lte=end,
            role__name='instructor',
            person__may_contact=True,
        ).exclude(event__tags__in=tags).order_by('event', 'person', 'role') \
         .select_related('person', 'event', 'role')
        return tasks

    @list_route(methods=['GET'])
    def instructors_by_time(self, request, format=None):
        """Workshops and instructors who taught in specific time period."""
        start, end = self._default_start_end_dates(
            start=self.request.query_params.get('start', None),
            end=self.request.query_params.get('end', None))
        tasks = self.instructors_by_time_queryset(start, end)
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
    queryset = Event.objects.all().select_related('host', 'administrator') \
                                  .prefetch_related('tags')
    serializer_class = EventSerializer
    lookup_field = 'slug'
    pagination_class = StandardResultsSetPagination
    filter_backends = (DjangoFilterBackend, )
    filter_class = EventFilter


class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """List tasks belonging to specific event."""
    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TaskSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = (DjangoFilterBackend, )
    filter_class = TaskFilter
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


class TodoViewSet(viewsets.ReadOnlyModelViewSet):
    """List todos belonging to specific event."""
    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TodoSerializer
    _event_slug = None

    def get_queryset(self):
        qs = TodoItem.objects.all()
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
                     .prefetch_related('badges', 'domains', 'lessons')
    serializer_class = PersonSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = (DjangoFilterBackend, )
    filter_class = PersonFilter


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
