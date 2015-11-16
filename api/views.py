import datetime

from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from workshops.models import Badge, Airport, Event, Role

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

    # Everyone who is an explicit member.
    member_badge = Badge.objects.get(name='member')
    queryset = member_badge.person_set.all()

    # This is a really clumsy way to add everyone who qualifies by having taught recently.
    today = datetime.date.today()
    cutoff = datetime.date(year=today.year-2, month=1, day=1)
    member_ids = set([p.id for p in queryset])
    instructor_badge = Badge.objects.get(name='instructor')
    instructors = instructor_badge.person_set.all()
    instructor_role = Role.objects.get(name='instructor')
    implicit_members = []
    for i in instructors:
        if i.id not in member_ids:
            tasks = i.task_set.filter(role=instructor_role)
            for t in tasks:
                if t.event.start is None:
                    import sys
                    print('Whoops, event has no start date {0}'.format(t.event), file=sys.stderr)
                    continue
                if t.event.start >= cutoff:
                    implicit_members.append(i)
                    member_ids.add(i.id)
                    break

    # Somehow have to add implicit_members to queryset


class PublishedEvents(ListAPIView):
    # only events that have both a starting date and a URL
    permission_classes = (IsAuthenticatedOrReadOnly, )
    paginator = None  # disable pagination

    serializer_class = EventSerializer
    queryset = Event.objects.published_events()
