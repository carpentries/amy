from collections import OrderedDict

from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.metadata import SimpleMetadata
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from api.filters import EventFilter, PersonFilter, TaskFilter, TrainingRequestFilterIDs
from api.renderers import (
    TrainingRequestCSVRenderer,
    TrainingRequestManualScoreCSVRenderer,
)
from api.serializers import (
    AirportSerializer,
    AwardSerializer,
    ConsentSerializer,
    EmailTemplateSerializer,
    EventSerializer,
    OrganizationSerializer,
    PersonSerializer,
    PersonSerializerAllData,
    TaskSerializer,
    TermSerializer,
    TrainingProgressSerializer,
    TrainingRequestForManualScoringSerializer,
    TrainingRequestWithPersonSerializer,
)
from autoemails.models import EmailTemplate
from consents.models import Consent, Term
from workshops.models import (
    Airport,
    Award,
    Event,
    Organization,
    Person,
    Task,
    TrainingProgress,
    TrainingRequest,
)


class IsAdmin(BasePermission):
    """This permission allows only admin users to view the API content."""

    def has_permission(self, request, view):
        return request.user.is_admin


class HasRestrictedPermission(BasePermission):
    """This permission allows only users with special
    'can_access_restricted_API' permission."""

    def has_permission(self, request, view):
        return request.user.has_perm("workshops.can_access_restricted_API")


class QueryMetadata(SimpleMetadata):
    """Additionally include info about query parameters."""

    def determine_metadata(self, request, view):
        data = super().determine_metadata(request, view)

        try:
            data["query_params"] = view.get_query_params_description()
        except AttributeError:
            pass

        return data


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 10000


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response(
            OrderedDict(
                [
                    (
                        "export-person-data",
                        reverse(
                            "api:export-person-data", request=request, format=format
                        ),
                    ),
                    (
                        "training-requests",
                        reverse(
                            "api:training-requests", request=request, format=format
                        ),
                    ),
                    # "new" API list-type endpoints below
                    (
                        "airport-list",
                        reverse("api:airport-list", request=request, format=format),
                    ),
                    (
                        "person-list",
                        reverse("api:person-list", request=request, format=format),
                    ),
                    (
                        "event-list",
                        reverse("api:event-list", request=request, format=format),
                    ),
                    (
                        "organization-list",
                        reverse(
                            "api:organization-list", request=request, format=format
                        ),
                    ),
                    (
                        "emailtemplate-list",
                        reverse(
                            "api:emailtemplate-list", request=request, format=format
                        ),
                    ),
                    (
                        "term-list",
                        reverse("api:term-list", request=request, format=format),
                    ),
                ]
            )
        )


class ExportPersonDataView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
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


class TrainingRequests(ListAPIView):
    permission_classes = (IsAuthenticated, IsAdmin)
    paginator = None
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [
        TrainingRequestCSVRenderer,
        TrainingRequestManualScoreCSVRenderer,
    ]
    queryset = (
        TrainingRequest.objects.all()
        .select_related("person")
        .prefetch_related(
            "previous_involvement",
            "domains",
            Prefetch(
                "person__award_set",
                queryset=Award.objects.select_related("badge"),
            ),
            Prefetch(
                "person__task_set",
                queryset=Task.objects.filter(
                    role__name="learner", event__tags__name="TTT"
                ).select_related("event"),
                to_attr="training_tasks",
            ),
        )
    )
    filterset_class = TrainingRequestFilterIDs

    def get_serializer_class(self):
        if self.request.query_params.get("manualscore"):
            return TrainingRequestForManualScoringSerializer
        else:
            return TrainingRequestWithPersonSerializer


# ----------------------
# "new" API starts below
# ----------------------


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """List many hosts or retrieve only one."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    lookup_field = "domain"
    lookup_value_regex = ".+"  # the default one doesn't work with domains with paths
    pagination_class = StandardResultsSetPagination


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """List many events or retrieve only one."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = (
        Event.objects.select_related("host", "administrator")
        .prefetch_related("tags")
        .attendance()
    )
    serializer_class = EventSerializer
    lookup_field = "slug"
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
        qs = Task.objects.all().select_related("person", "role", "person__airport")
        if self._event_slug:
            qs = qs.filter(event__slug=self._event_slug)
        return qs

    def list(self, request, event_slug=None):
        self._event_slug = event_slug
        return super().list(request)

    def retrieve(self, request, pk=None, event_slug=None):
        self._event_slug = event_slug
        return super().retrieve(request, pk=pk)


class TermViewSet(viewsets.ReadOnlyModelViewSet):
    """List many active terms or retrieve only one active term."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Term.objects.active()
    serializer_class = TermSerializer
    pagination_class = StandardResultsSetPagination


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    """List many people or retrieve only one person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = (
        Person.objects.all()
        .select_related("airport")
        .prefetch_related("badges", "domains", "lessons")
        .distinct()
    )
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


class PersonConsentViewSet(viewsets.ReadOnlyModelViewSet):
    """List consents agreed to by a specific person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = ConsentSerializer
    _person_pk = None

    def get_queryset(self):
        qs = Consent.objects.active()
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
    lookup_field = "iata__iexact"
    lookup_url_kwarg = "iata"
    pagination_class = StandardResultsSetPagination


class EmailTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """List email templates ReadOnly."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    lookup_field = "slug"


class TrainingProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """List training progresses belonging to specific person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TrainingProgressSerializer
    _person_pk = None

    def get_queryset(self):
        qs = TrainingProgress.objects.all()
        if self._person_pk:
            qs = qs.filter(trainee=self._person_pk)
        return qs

    def list(self, request, person_pk=None):
        self._person_pk = person_pk
        return super().list(request)

    def retrieve(self, request, pk=None, person_pk=None):
        self._person_pk = person_pk
        return super().retrieve(request, pk=pk)
