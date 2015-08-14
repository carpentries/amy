from django.db.models import Q
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
            'events-published': reverse('api:events-published',
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


class ListEvents(APIView):
    # I wanted to use ListAPIView, but it had problems with the way we test
    # this code... Basically ListAPIView uses pagination, and pagination
    # requires existing Request object - something we're faking in part of the
    # tests (request = None).
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    queryset = None  # override this in the subclass

    def get(self, request, format=None):
        objects = self.queryset.all()
        serializer = self.serializer_class(objects, many=True)
        return Response(serializer.data)


class PublishedEvents(ListEvents):
    # only events that have both a starting date and a URL
    queryset = Event.objects.exclude(
        Q(start__isnull=True) | Q(url__isnull=True)
    ).order_by('-start')
