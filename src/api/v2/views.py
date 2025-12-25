from typing import Any

from django.utils import timezone
from knox.auth import TokenAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from src.api.v2.permissions import ApiAccessPermission
from src.api.v2.serializers import (
    AttachmentPresignedUrlPayloadSerializer,
    AttachmentSerializer,
    AwardSerializer,
    EventSerializer,
    InstructorRecruitmentSignupSerializer,
    MembershipSerializer,
    OrganizationSerializer,
    PersonSerializer,
    ScheduledEmailLogDetailsSerializer,
    ScheduledEmailSerializer,
    SelfOrganisedSubmissionSerializer,
    TaskSerializer,
    TrainingProgressSerializer,
    TrainingRequirementSerializer,
)
from src.emails.controller import EmailController
from src.emails.models import Attachment, ScheduledEmail, ScheduledEmailStatus
from src.extrequests.models import SelfOrganisedSubmission
from src.recruitment.models import InstructorRecruitmentSignup
from src.workshops.models import (
    Award,
    Event,
    Membership,
    Organization,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)


class AuthenticatedRequest(Request):
    user: Person


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 1000


class AwardViewSet(viewsets.ReadOnlyModelViewSet[Award]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = Award.objects.select_related("person", "badge", "event", "awarded_by").order_by("pk").all()
    serializer_class = AwardSerializer
    pagination_class = StandardResultsSetPagination


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet[Organization]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = Organization.objects.prefetch_related("affiliated_organizations").order_by("pk").all()
    serializer_class = OrganizationSerializer
    pagination_class = StandardResultsSetPagination


class EventViewSet(viewsets.ReadOnlyModelViewSet[Event]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = (
        Event.objects.select_related("host", "sponsor", "membership", "administrator", "language", "assigned_to")
        .prefetch_related("tags", "curricula", "lessons")
        .order_by("pk")
        .all()
    )
    serializer_class = EventSerializer
    pagination_class = StandardResultsSetPagination


class InstructorRecruitmentSignupViewSet(viewsets.ReadOnlyModelViewSet[InstructorRecruitmentSignup]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = (
        InstructorRecruitmentSignup.objects.select_related("recruitment", "recruitment__event", "person")
        .order_by("pk")
        .all()
    )
    serializer_class = InstructorRecruitmentSignupSerializer
    pagination_class = StandardResultsSetPagination


class MembershipViewSet(viewsets.ReadOnlyModelViewSet[Membership]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = Membership.objects.prefetch_related("organizations", "persons").order_by("pk").all()
    serializer_class = MembershipSerializer
    pagination_class = StandardResultsSetPagination


class PersonViewSet(viewsets.ReadOnlyModelViewSet[Person]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    pagination_class = StandardResultsSetPagination


class ScheduledEmailViewSet(viewsets.ReadOnlyModelViewSet[ScheduledEmail]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = (
        ScheduledEmail.objects.select_related("template", "generic_relation_content_type").order_by("created_at").all()
    )
    serializer_class = ScheduledEmailSerializer
    pagination_class = StandardResultsSetPagination

    @action(detail=False)
    def scheduled_to_run(self, request: Request) -> Response:
        now = timezone.now()
        scheduled_emails = ScheduledEmail.objects.filter(
            state__in=[ScheduledEmailStatus.SCHEDULED, ScheduledEmailStatus.FAILED],
            scheduled_at__lte=now,
        ).order_by("-created_at")

        page = self.paginate_queryset(scheduled_emails)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(scheduled_emails, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def lock(self, request: AuthenticatedRequest, pk: str | None = None) -> Response:
        email = self.get_object()
        locked_email = EmailController.lock_email(email, "State changed by worker", request.user)
        return Response(self.get_serializer(locked_email).data)

    @action(detail=True, methods=["post"])
    def fail(self, request: AuthenticatedRequest, pk: str | None = None) -> Response:
        email = self.get_object()
        serializer = ScheduledEmailLogDetailsSerializer[dict[str, Any]](data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        locked_email = EmailController.fail_email(email, serializer.validated_data["details"], request.user)
        return Response(self.get_serializer(locked_email).data)

    @action(detail=True, methods=["post"])
    def succeed(self, request: AuthenticatedRequest, pk: str | None = None) -> Response:
        email = self.get_object()
        serializer = ScheduledEmailLogDetailsSerializer[dict[str, Any]](data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        locked_email = EmailController.succeed_email(email, serializer.validated_data["details"], request.user)
        return Response(self.get_serializer(locked_email).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request: AuthenticatedRequest, pk: str | None = None) -> Response:
        email = self.get_object()
        serializer = ScheduledEmailLogDetailsSerializer[dict[str, Any]](data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        locked_email = EmailController.cancel_email(email, serializer.validated_data["details"], request.user)
        return Response(self.get_serializer(locked_email).data)


class AttachmentViewSet(viewsets.ReadOnlyModelViewSet[Attachment]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = Attachment.objects.order_by("created_at").all()
    serializer_class = AttachmentSerializer
    pagination_class = StandardResultsSetPagination

    @action(detail=True, methods=["post"])
    def generate_presigned_url(self, request: Request, pk: str | None = None) -> Response:
        serializer = AttachmentPresignedUrlPayloadSerializer[dict[str, Any]](data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        attachment = self.get_object()
        attachment_with_presigned_url = EmailController.generate_presigned_url_for_attachment(
            attachment,
            expiration_seconds=serializer.validated_data["expiration_seconds"],
        )
        return Response(self.get_serializer(attachment_with_presigned_url).data)


class TaskViewSet(viewsets.ReadOnlyModelViewSet[Task]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = Task.objects.select_related("person", "event", "role", "seat_membership").order_by("pk").all()
    serializer_class = TaskSerializer
    pagination_class = StandardResultsSetPagination


class TrainingProgressViewSet(viewsets.ReadOnlyModelViewSet[TrainingProgress]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = (
        TrainingProgress.objects.select_related("trainee", "requirement", "involvement_type", "event")
        .order_by("pk")
        .all()
    )
    serializer_class = TrainingProgressSerializer
    pagination_class = StandardResultsSetPagination


class TrainingRequirementViewSet(viewsets.ReadOnlyModelViewSet[TrainingRequirement]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )
    queryset = TrainingRequirement.objects.order_by("pk").all()
    serializer_class = TrainingRequirementSerializer
    pagination_class = StandardResultsSetPagination


class SelfOrganisedSubmissionViewSet(viewsets.ReadOnlyModelViewSet[SelfOrganisedSubmission]):
    authentication_classes = (
        TokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        ApiAccessPermission,
    )

    queryset = SelfOrganisedSubmission.objects.order_by("pk").all()
    serializer_class = SelfOrganisedSubmissionSerializer
    pagination_class = StandardResultsSetPagination
