from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from workshops.models import Badge, Airport

from .serializers import (
    ExportBadgesSerializer,
    ExportInstructorLocationsSerializer,
)


class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'export-badges': reverse('export-badges', request=request,
                                     format=format),
            'export-instructors': reverse('export-instructors',
                                          request=request, format=format)
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
