from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from workshops.models import Badge, Airport, Event

from .serializers import (
    ExportBadgesSerializer,
    ExportInstructorLocationsSerializer,
    EventSerializer,
)


class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'export-badges': reverse('api:export-badges', request=request,
                                     format=format),
            'export-instructors': reverse('api:export-instructors',
                                          request=request, format=format),
            'events-past': reverse('api:events-past',
                                   request=request, format=format),
            'events-ongoing': reverse('api:events-ongoing',
                                      request=request, format=format),
            'events-upcoming': reverse('api:events-upcoming',
                                       request=request, format=format),
        })


class ExportBadgesView(APIView):
    """List all badges and people who have them."""
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def get(self, request, format=None):
        badges = Badge.objects.prefetch_related('person_set')
        serializer = ExportBadgesSerializer(badges, many=True)
        return Response(serializer.data)


class ExportInstructorLocationsView(APIView):
    """List all airports and instructors located near them."""
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def get(self, request, format=None):
        # TODO: return only people marked as instructors?
        airports = Airport.objects.exclude(person=None) \
                                  .prefetch_related('person_set')
        serializer = ExportInstructorLocationsSerializer(airports, many=True)
        return Response(serializer.data)


class ListEvents(ListAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class PastEvents(ListEvents):
    queryset = Event.objects.past_events()


class OngoingEvents(ListEvents):
    queryset = Event.objects.ongoing_events()


class UpcomingEvents(ListEvents):
    queryset = Event.objects.upcoming_events()
