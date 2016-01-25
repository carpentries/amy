import datetime

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.filters import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.metadata import SimpleMetadata
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    IsAuthenticatedOrReadOnly, IsAuthenticated
)
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from workshops.models import (
    Badge,
    Airport,
    Event,
    TodoItem,
    Tag,
    Host,
    Task,
    Award,
    Person,
)
from workshops.util import get_members, default_membership_cutoff

from .serializers import (
    PersonNameEmailSerializer,
    ExportBadgesSerializer,
    ExportInstructorLocationsSerializer,
    ExportEventSerializer,
    TimelineTodoSerializer,
    HostSerializer,
    EventSerializer,
    TaskSerializer,
    TodoSerializer,
    AirportSerializer,
    AwardSerializer,
    PersonSerializer,
)

from .filters import EventFilter, TaskFilter


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
            'export-instructors': reverse('api:export-instructors',
                                          request=request, format=format),
            'export-members': reverse('api:export-members', request=request,
                                      format=format),
            'events-published': reverse('api:events-published',
                                        request=request, format=format),
            'user-todos': reverse('api:user-todos',
                                  request=request, format=format),

            # "new" API list-type endpoints below
            'airport-list': reverse('api:airport-list', request=request,
                                    format=format),
            'person-list': reverse('api:person-list', request=request,
                                   format=format),
            'event-list': reverse('api:event-list', request=request,
                                  format=format),
            'host-list': reverse('api:host-list', request=request,
                                 format=format),
        })


class ExportBadgesView(ListAPIView):
    """List all badges and people who have them."""
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    queryset = Badge.objects.prefetch_related('person_set')
    serializer_class = ExportBadgesSerializer


class ExportInstructorLocationsView(ListAPIView):
    """List all airports and instructors located near them."""
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    queryset = Airport.objects.exclude(person=None) \
                              .prefetch_related('person_set')
    serializer_class = ExportInstructorLocationsSerializer


class ExportMembersView(ListAPIView):
    """Show everyone who qualifies as an SCF member."""
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    serializer_class = PersonNameEmailSerializer

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
    permission_classes = (IsAuthenticated, )
    paginator = None
    serializer_class = TimelineTodoSerializer

    def get_queryset(self):
        """Return current TODOs for currently logged in user."""
        return TodoItem.objects.user(self.request.user) \
                               .incomplete() \
                               .exclude(due=None) \
                               .select_related('event')

# ----------------------
# "new" API starts below
# ----------------------


class HostViewSet(viewsets.ReadOnlyModelViewSet):
    """List many hosts or retrieve only one."""
    permission_classes = (IsAuthenticated, )
    queryset = Host.objects.all()
    serializer_class = HostSerializer
    lookup_field = 'domain'
    lookup_value_regex = r'[^/]+'  # the default one doesn't work with domains
    pagination_class = StandardResultsSetPagination


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """List many events or retrieve only one."""
    permission_classes = (IsAuthenticated, )
    queryset = Event.objects.all().select_related('host', 'administrator') \
                                  .prefetch_related('tags')
    serializer_class = EventSerializer
    lookup_field = 'slug'
    pagination_class = StandardResultsSetPagination
    filter_backends = (DjangoFilterBackend, )
    filter_class = EventFilter


class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """List tasks belonging to specific event."""
    permission_classes = (IsAuthenticated, )
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
    permission_classes = (IsAuthenticated, )
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
    permission_classes = (IsAuthenticated, )
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    pagination_class = StandardResultsSetPagination


class AwardViewSet(viewsets.ReadOnlyModelViewSet):
    """List awards belonging to specific person."""
    permission_classes = (IsAuthenticated, )
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


class AirportViewSet(viewsets.ReadOnlyModelViewSet):
    """List many airports or retrieve only one."""
    permission_classes = (IsAuthenticated, )
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    lookup_field = 'iata'
    pagination_class = StandardResultsSetPagination
