# from knox.auth import TokenAuthentication
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from api.v2.serializers import (
    AwardSerializer,
    EventSerializer,
    InstructorRecruitmentSignupSerializer,
    MembershipSerializer,
    PersonSerializer,
    ScheduledEmailSerializer,
    TrainingProgressSerializer,
    TrainingRequirementSerializer,
)
from emails.models import ScheduledEmail
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import (
    Award,
    Event,
    Membership,
    Person,
    TrainingProgress,
    TrainingRequirement,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 1000


class AwardViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = (
        Award.objects.select_related("person", "badge", "event", "awarded_by")
        .order_by("pk")
        .all()
    )
    serializer_class = AwardSerializer
    pagination_class = StandardResultsSetPagination


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = (
        Event.objects.select_related(
            "host", "sponsor", "membership", "administrator", "language", "assigned_to"
        )
        .prefetch_related("tags", "curricula", "lessons")
        .order_by("pk")
        .all()
    )
    serializer_class = EventSerializer
    pagination_class = StandardResultsSetPagination


class InstructorRecruitmentSignupViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = (
        InstructorRecruitmentSignup.objects.select_related(
            "recruitment", "recruitment__event", "person"
        )
        .order_by("pk")
        .all()
    )
    serializer_class = InstructorRecruitmentSignupSerializer
    pagination_class = StandardResultsSetPagination


class MembershipViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = (
        Membership.objects.prefetch_related("organizations", "persons")
        .order_by("pk")
        .all()
    )
    serializer_class = MembershipSerializer
    pagination_class = StandardResultsSetPagination


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = Person.objects.select_related("airport").all()
    serializer_class = PersonSerializer
    pagination_class = StandardResultsSetPagination


class ScheduledEmailViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = (
        ScheduledEmail.objects.select_related(
            "template", "generic_relation_content_type"
        )
        .order_by("created_at")
        .all()
    )
    serializer_class = ScheduledEmailSerializer
    pagination_class = StandardResultsSetPagination


class TrainingProgressViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = (
        TrainingProgress.objects.select_related(
            "trainee", "requirement", "involvement_type", "event"
        )
        .order_by("pk")
        .all()
    )
    serializer_class = TrainingProgressSerializer
    pagination_class = StandardResultsSetPagination


class TrainingRequirementViewSet(viewsets.ReadOnlyModelViewSet):
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = TrainingRequirement.objects.order_by("pk").all()
    serializer_class = TrainingRequirementSerializer
    pagination_class = StandardResultsSetPagination
