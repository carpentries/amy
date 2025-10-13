from collections import OrderedDict
from typing import Any, cast

from django.contrib.auth.models import AnonymousUser
from django.db.models import Prefetch, Q, QuerySet
from rest_framework import viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.metadata import SimpleMetadata
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from api.v1.filters import (
    EventFilter,
    PersonFilter,
    TaskFilter,
    TrainingRequestFilterIDs,
)
from api.v1.permissions import DjangoModelPermissionsWithView
from api.v1.renderers import (
    TrainingRequestCSVRenderer,
    TrainingRequestManualScoreCSVRenderer,
)
from api.v1.serializers import (
    AwardSerializer,
    CommunityRoleConfigSerializer,
    ConsentSerializer,
    EventSerializer,
    InstructorRecruitmentSerializer,
    OrganizationSerializer,
    PersonSerializer,
    PersonSerializerAllData,
    TaskSerializer,
    TermSerializer,
    TrainingProgressSerializer,
    TrainingRequestForManualScoringSerializer,
    TrainingRequestSerializer,
    TrainingRequestWithPersonSerializer,
)
from communityroles.models import CommunityRoleConfig
from consents.models import Consent, Term
from recruitment.models import InstructorRecruitment
from workshops.models import (
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

    def has_permission(self, request: Request, view: APIView) -> bool:
        return not isinstance(request.user, AnonymousUser) and request.user.is_admin


class HasRestrictedPermission(BasePermission):
    """This permission allows only users with special
    'can_access_restricted_API' permission."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return not isinstance(request.user, AnonymousUser) and request.user.has_perm(
            "workshops.can_access_restricted_API"
        )


class QueryMetadata(SimpleMetadata):
    """Additionally include info about query parameters."""

    def determine_metadata(self, request: Request, view: APIView) -> Any:
        data = super().determine_metadata(request, view)

        try:
            data["query_params"] = view.get_query_params_description()  # type: ignore
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
    def get(self, request: Request, format: str | None = None) -> Response:
        return Response(
            OrderedDict(
                [
                    (
                        "export-person-data",
                        reverse("api-v1:export-person-data", request=request, format=format),
                    ),
                    (
                        "training-requests",
                        reverse("api-v1:training-requests", request=request, format=format),
                    ),
                    # "new" API list-type endpoints below
                    (
                        "person-list",
                        reverse("api-v1:person-list", request=request, format=format),
                    ),
                    (
                        "event-list",
                        reverse("api-v1:event-list", request=request, format=format),
                    ),
                    (
                        "organization-list",
                        reverse("api-v1:organization-list", request=request, format=format),
                    ),
                    (
                        "term-list",
                        reverse("api-v1:term-list", request=request, format=format),
                    ),
                    (
                        "communityroleconfig-list",
                        reverse(
                            "api-v1:communityroleconfig-list",
                            request=request,
                            format=format,
                        ),
                    ),
                    (
                        "instructorrecruitment-list",
                        reverse(
                            "api-v1:instructorrecruitment-list",
                            request=request,
                            format=format,
                        ),
                    ),
                ]
            )
        )


class ExportPersonDataView(RetrieveAPIView[Person]):
    permission_classes = (IsAuthenticated,)
    serializer_class = PersonSerializerAllData
    queryset = Person.objects.all()

    def get_object(self) -> Person:
        """Get logged-in user data, make it impossible to gather someone else's
        data this way."""
        user = self.request.user

        if user.is_anonymous:
            return self.get_queryset().none()  # type: ignore
        else:
            return self.get_queryset().get(pk=cast(int, user.pk))


class TrainingRequests(ListAPIView[TrainingRequest]):
    permission_classes = (IsAuthenticated, IsAdmin)
    paginator = None
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [  # type: ignore
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
                queryset=Task.objects.filter(role__name="learner", event__tags__name="TTT").select_related("event"),
                to_attr="training_tasks",
            ),
        )
    )
    filterset_class = TrainingRequestFilterIDs

    def get_serializer_class(self) -> type[TrainingRequestSerializer]:
        if self.request.query_params.get("manualscore"):
            return TrainingRequestForManualScoringSerializer
        else:
            return TrainingRequestWithPersonSerializer


# ----------------------
# "new" API starts below
# ----------------------


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet[Organization]):
    """List many hosts or retrieve only one."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    lookup_field = "domain"
    lookup_value_regex = ".+"  # the default one doesn't work with domains with paths
    pagination_class = StandardResultsSetPagination


class EventViewSet(viewsets.ReadOnlyModelViewSet[Event]):
    """List many events or retrieve only one."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Event.objects.attendance().select_related("host", "administrator").prefetch_related("tags")
    serializer_class = EventSerializer
    lookup_field = "slug"
    pagination_class = StandardResultsSetPagination
    filterset_class = EventFilter


class TaskViewSet(viewsets.ReadOnlyModelViewSet[Task]):
    """List tasks belonging to specific event."""

    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TaskSerializer
    pagination_class = StandardResultsSetPagination
    filterset_class = TaskFilter
    _event_slug = None

    def get_queryset(self) -> QuerySet[Task]:
        qs = Task.objects.all().select_related("person", "role")
        if self._event_slug:
            qs = qs.filter(event__slug=self._event_slug)
        return qs

    def list(self, request: Request, event_slug: str | None = None) -> Response:
        self._event_slug = event_slug
        return super().list(request)

    def retrieve(self, request: Request, pk: int | None = None, event_slug: str | None = None) -> Response:
        self._event_slug = event_slug
        return super().retrieve(request, pk=pk)


class TermViewSet(viewsets.ReadOnlyModelViewSet[Term]):
    """List many active terms or retrieve only one active term."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Term.objects.active()
    serializer_class = TermSerializer
    pagination_class = StandardResultsSetPagination


class PersonViewSet(viewsets.ReadOnlyModelViewSet[Person]):
    """List many people or retrieve only one person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    queryset = Person.objects.all().prefetch_related("badges", "domains", "lessons", "languages").distinct()
    serializer_class = PersonSerializer
    pagination_class = StandardResultsSetPagination
    filterset_class = PersonFilter


class AwardViewSet(viewsets.ReadOnlyModelViewSet[Award]):
    """List awards belonging to specific person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = AwardSerializer
    _person_pk = None

    def get_queryset(self) -> QuerySet[Award]:
        qs = Award.objects.all()
        if self._person_pk:
            qs = qs.filter(person=self._person_pk)
        return qs

    def list(self, request: Request, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().list(request)

    def retrieve(self, request: Request, pk: int | None = None, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().retrieve(request, pk=pk)


class PersonTaskViewSet(viewsets.ReadOnlyModelViewSet[Task]):
    """List tasks done by specific person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TaskSerializer
    _person_pk = None

    def get_queryset(self) -> QuerySet[Task]:
        qs = Task.objects.all()
        if self._person_pk:
            qs = qs.filter(person=self._person_pk)
        return qs

    def list(self, request: Request, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().list(request)

    def retrieve(self, request: Request, pk: int | None = None, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().retrieve(request, pk=pk)


class PersonConsentViewSet(viewsets.ReadOnlyModelViewSet[Consent]):
    """List consents agreed to by a specific person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = ConsentSerializer
    _person_pk = None

    def get_queryset(self) -> QuerySet[Consent]:
        qs = Consent.objects.active()
        if self._person_pk:
            qs = qs.filter(person=self._person_pk)
        return qs

    def list(self, request: Request, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().list(request)

    def retrieve(self, request: Request, pk: int | None = None, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().retrieve(request, pk=pk)


class TrainingProgressViewSet(viewsets.ReadOnlyModelViewSet[TrainingProgress]):
    """List training progresses belonging to specific person."""

    permission_classes = (IsAuthenticated, IsAdmin)
    serializer_class = TrainingProgressSerializer
    _person_pk = None

    def get_queryset(self) -> QuerySet[TrainingProgress]:
        qs = TrainingProgress.objects.all()
        if self._person_pk:
            qs = qs.filter(trainee=self._person_pk)
        return qs

    def list(self, request: Request, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().list(request)

    def retrieve(self, request: Request, pk: int | None = None, person_pk: int | None = None) -> Response:
        self._person_pk = person_pk
        return super().retrieve(request, pk=pk)


class CommunityRoleConfigViewSet(viewsets.ReadOnlyModelViewSet[CommunityRoleConfig]):
    """List existing Community Role Configurations."""

    permission_classes = (IsAuthenticated,)
    serializer_class = CommunityRoleConfigSerializer

    def get_queryset(self) -> QuerySet[CommunityRoleConfig]:
        qs = CommunityRoleConfig.objects.all()

        if term := self.request.GET.get("term"):
            qs = qs.filter(Q(name__icontains=term) | Q(display_name__icontains=term))

        return qs


class InstructorRecruitmentViewSet(viewsets.ModelViewSet[InstructorRecruitment]):
    """List/add/edit/delete Instructor Recruitments."""

    permission_classes = (DjangoModelPermissionsWithView,)
    serializer_class = InstructorRecruitmentSerializer
    queryset = InstructorRecruitment.objects.all()
