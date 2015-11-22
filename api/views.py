from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from workshops.models import Badge, Airport, Event
from workshops.util import get_members

from .serializers import (
    ExportBadgesSerializer,
    ExportInstructorLocationsSerializer,
    ExportMembersSerializer,
    EventSerializer,
)


class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'export-badges': reverse('api:export-badges', request=request,
                                     format=format),
            'export-instructors': reverse('api:export-instructors',
                                          request=request, format=format),
            'events-published': reverse('api:events-published',
                                        request=request, format=format),
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

    serializer_class = ExportMembersSerializer

    def get_queryset(self):
        return get_members()


class PublishedEvents(ListAPIView):
    # only events that have both a starting date and a URL
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    serializer_class = EventSerializer
    queryset = Event.objects.published_events()
