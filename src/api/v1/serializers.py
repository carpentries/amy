from typing import Any

from rest_framework import serializers

from src.communityroles.models import CommunityRoleConfig
from src.consents.models import Consent, Term, TermOption
from src.recruitment.models import InstructorRecruitment
from src.trainings.models import Involvement
from src.workshops.models import (
    Award,
    Badge,
    Event,
    KnowledgeDomain,
    Language,
    Lesson,
    Organization,
    Person,
    Role,
    Tag,
    Task,
    TrainingProgress,
    TrainingRequest,
    TrainingRequirement,
)


class PersonNameSerializer(serializers.ModelSerializer[Person]):
    name = serializers.CharField(source="full_name")

    class Meta:
        model = Person
        fields = ("name",)


class BadgeSerializer(serializers.ModelSerializer[Badge]):
    class Meta:
        model = Badge
        fields = ("name", "title", "criteria")


# ----------------------
# "new" API starts below
# ----------------------


class OrganizationSerializer(serializers.ModelSerializer[Organization]):
    country = serializers.CharField()

    class Meta:
        model = Organization
        fields = ("domain", "fullname", "country")


class AwardSerializer(serializers.ModelSerializer[Award]):
    badge = serializers.SlugRelatedField[Badge](many=False, read_only=True, slug_field="name")
    event = serializers.HyperlinkedRelatedField[Event](
        read_only=True, view_name="api-v1:event-detail", lookup_field="slug"
    )

    class Meta:
        model = Award
        fields = ("badge", "awarded", "event")


class TermSerializer(serializers.ModelSerializer[Term]):
    class Meta:
        model = Term
        fields = ("slug", "content", "required_type", "help_text")


class ConsentSerializer(serializers.ModelSerializer[Consent]):
    term = TermSerializer(read_only=True)
    term_option = serializers.StringRelatedField[TermOption]()

    class Meta:
        model = Consent
        fields = ("term", "term_option")


class PersonSerializer(serializers.ModelSerializer[Person]):
    airport_iata = serializers.CharField()
    country = serializers.CharField()
    timezone = serializers.CharField()
    lessons = serializers.SlugRelatedField[Lesson](many=True, read_only=True, slug_field="name")
    domains = serializers.SlugRelatedField[KnowledgeDomain](many=True, read_only=True, slug_field="name")
    badges = serializers.SlugRelatedField[Badge](many=True, read_only=True, slug_field="name")
    awards = serializers.HyperlinkedIdentityField(
        view_name="api-v1:person-awards-list",
        lookup_field="pk",
        lookup_url_kwarg="person_pk",
    )
    tasks = serializers.HyperlinkedIdentityField(
        view_name="api-v1:person-tasks-list",
        lookup_field="pk",
        lookup_url_kwarg="person_pk",
    )
    consents = serializers.HyperlinkedIdentityField(
        view_name="api-v1:person-consents-list",
        lookup_field="pk",
        lookup_url_kwarg="person_pk",
    )

    class Meta:
        model = Person
        fields = (
            "username",
            "personal",
            "middle",
            "family",
            "email",
            "secondary_email",
            "gender",
            "gender_other",
            "airport_iata",
            "country",
            "timezone",
            "github",
            "twitter",
            "bluesky",
            "mastodon",
            "url",
            "orcid",
            "affiliation",
            "occupation",
            "badges",
            "lessons",
            "languages",
            "domains",
            "awards",
            "tasks",
            "consents",
        )


class TaskSerializer(serializers.ModelSerializer[Task]):
    event = serializers.HyperlinkedRelatedField[Event](
        read_only=True, view_name="api-v1:event-detail", lookup_field="slug"
    )
    person = serializers.HyperlinkedRelatedField[Person](read_only=True, view_name="api-v1:person-detail")
    role = serializers.SlugRelatedField[Role](many=False, read_only=True, slug_field="name")

    class Meta:
        model = Task
        fields = ("event", "person", "role")


class EventSerializer(serializers.ModelSerializer[Event]):
    country = serializers.CharField()
    start = serializers.DateField(format=None)
    end = serializers.DateField(format=None)

    host = serializers.HyperlinkedRelatedField[Organization](
        read_only=True, view_name="api-v1:organization-detail", lookup_field="domain"
    )
    administrator = serializers.HyperlinkedRelatedField[Organization](
        read_only=True, view_name="api-v1:organization-detail", lookup_field="domain"
    )
    tags = serializers.SlugRelatedField[Tag](many=True, read_only=True, slug_field="name")
    tasks = serializers.HyperlinkedIdentityField(
        view_name="api-v1:event-tasks-list",
        lookup_field="slug",
        lookup_url_kwarg="event_slug",
    )
    assigned_to = serializers.HyperlinkedRelatedField[Person](read_only=True, view_name="api-v1:person-detail")
    attendance = serializers.IntegerField()

    class Meta:
        model = Event
        fields = (
            "slug",
            "completed",
            "start",
            "end",
            "host",
            "administrator",
            "tags",
            "website_url",
            "reg_key",
            "attendance",
            "contact",
            "country",
            "venue",
            "address",
            "latitude",
            "longitude",
            "tasks",
            "assigned_to",
        )


class TrainingRequestSerializer(serializers.ModelSerializer[TrainingRequest]):
    state = serializers.CharField(source="get_state_display")
    domains = serializers.SlugRelatedField[KnowledgeDomain](many=True, read_only=True, slug_field="name")
    previous_involvement = serializers.SlugRelatedField[Involvement](many=True, read_only=True, slug_field="name")
    previous_training = serializers.CharField(source="get_previous_training_display")
    previous_experience = serializers.CharField(source="get_previous_experience_display")
    programming_language_usage_frequency = serializers.CharField(
        source="get_programming_language_usage_frequency_display"
    )
    checkout_intent = serializers.CharField(source="get_checkout_intent_display")
    teaching_intent = serializers.CharField(source="get_teaching_intent_display")
    teaching_frequency_expectation = serializers.CharField(source="get_teaching_frequency_expectation_display")
    max_travelling_frequency = serializers.CharField(source="get_max_travelling_frequency_display")

    class Meta:
        model = TrainingRequest
        fields = (
            "created_at",
            "last_updated_at",
            "state",
            "review_process",
            "member_code",
            "personal",
            "middle",
            "family",
            "email",
            "secondary_email",
            "github",
            "occupation",
            "occupation_other",
            "affiliation",
            "location",
            "country",
            "underresourced",
            "underrepresented",
            "underrepresented_details",
            "domains",
            "domains_other",
            "nonprofit_teaching_experience",
            "previous_involvement",
            "previous_training",
            "previous_training_other",
            "previous_training_explanation",
            "previous_experience",
            "previous_experience_other",
            "previous_experience_explanation",
            "programming_language_usage_frequency",
            "checkout_intent",
            "teaching_intent",
            "teaching_frequency_expectation",
            "teaching_frequency_expectation_other",
            "max_travelling_frequency",
            "max_travelling_frequency_other",
            "reason",
            "user_notes",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
        )


class TrainingRequestWithPersonSerializer(TrainingRequestSerializer):
    person = serializers.SlugRelatedField[Person](many=False, read_only=True, slug_field="full_name")
    person_id = serializers.PrimaryKeyRelatedField[Person](many=False, read_only=True, source="person")
    domains = serializers.SerializerMethodField()  # type: ignore
    previous_involvement = serializers.SerializerMethodField()  # type: ignore
    awards = serializers.SerializerMethodField()
    training_tasks = serializers.SerializerMethodField()

    def get_domains(self, obj: TrainingRequest) -> str:
        return ", ".join(map(lambda x: x.name, obj.domains.all()))

    def get_previous_involvement(self, obj: TrainingRequest) -> str:
        return ", ".join(map(lambda x: x.name, obj.previous_involvement.all()))

    def get_awards(self, obj: TrainingRequest) -> str:
        if obj.person:
            return ", ".join(
                map(
                    lambda x: f"{x.badge.name} {x.awarded:%Y-%m-%d}",
                    obj.person.award_set.all(),
                )
            )
        else:
            return ""

    def get_training_tasks(self, obj: TrainingRequest) -> str:
        if obj.person:
            return ", ".join(map(lambda x: x.event.slug, obj.person.training_tasks))  # type: ignore
        else:
            return ""

    class Meta:
        model = TrainingRequest
        fields = (
            "created_at",
            "last_updated_at",
            "state",
            "person",
            "person_id",
            "awards",
            "training_tasks",
            "review_process",
            "member_code",
            "personal",
            "middle",
            "family",
            "email",
            "secondary_email",
            "github",
            "underrepresented",
            "underrepresented_details",
            "occupation",
            "occupation_other",
            "affiliation",
            "location",
            "country",
            "underresourced",
            "domains",
            "domains_other",
            "nonprofit_teaching_experience",
            "previous_involvement",
            "previous_training",
            "previous_training_other",
            "previous_training_explanation",
            "previous_experience",
            "previous_experience_other",
            "previous_experience_explanation",
            "programming_language_usage_frequency",
            "checkout_intent",
            "teaching_intent",
            "teaching_frequency_expectation",
            "teaching_frequency_expectation_other",
            "max_travelling_frequency",
            "max_travelling_frequency_other",
            "reason",
            "user_notes",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
        )


class TrainingRequestForManualScoringSerializer(TrainingRequestSerializer):
    request_id = serializers.IntegerField(source="pk")

    class Meta:
        model = TrainingRequest
        fields = (
            "request_id",
            "score_manual",
            "score_notes",
            "review_process",
            "member_code",
            "personal",
            "middle",
            "family",
            "affiliation",
            "nonprofit_teaching_experience",
            "previous_training",
            "previous_training_other",
            "previous_training_explanation",
            "previous_experience",
            "previous_experience_other",
            "previous_experience_explanation",
            "checkout_intent",
            "teaching_intent",
            "teaching_frequency_expectation",
            "teaching_frequency_expectation_other",
            "max_travelling_frequency",
            "max_travelling_frequency_other",
            "reason",
            "user_notes",
        )


# The serializers below are meant to help display user's data without any
# links in relational fields; instead, either an expanded model is displayed,
# or - if it's simple enough - its' string representation.
# The serializers are used mostly in ExportPersonDataView.


class EventSerializerSimplified(EventSerializer):
    class Meta:
        model = Event
        fields = (
            "slug",
            "start",
            "end",
            "tags",
            "website_url",
            "venue",
            "address",
            "country",
            "latitude",
            "longitude",
        )


class AwardSerializerExpandEvent(AwardSerializer):
    event = EventSerializerSimplified(many=False, read_only=True)  # type: ignore


class TrainingRequirementSerializer(serializers.ModelSerializer[TrainingRequirement]):
    class Meta:
        model = TrainingRequirement
        fields = (
            "name",
            "url_required",
            "event_required",
            "involvement_required",
        )


class InvolvementSerializer(serializers.ModelSerializer[Involvement]):
    class Meta:
        model = Involvement
        fields = (
            "name",
            "display_name",
            "url_required",
            "date_required",
            "notes_required",
        )


class TrainingProgressSerializer(serializers.ModelSerializer[TrainingProgress]):
    requirement = TrainingRequirementSerializer(many=False, read_only=True)
    involvement_type = InvolvementSerializer(many=False, read_only=True)
    state = serializers.CharField(source="get_state_display")
    event = EventSerializerSimplified(many=False, read_only=True)

    class Meta:
        model = TrainingProgress
        fields = (
            "created_at",
            "last_updated_at",
            "requirement",
            "involvement_type",
            "state",
            "event",
            "url",
            "date",
            "trainee_notes",
        )


class TaskSerializerNoPerson(TaskSerializer):
    event = EventSerializerSimplified(many=False, read_only=True)  # type: ignore
    role = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")

    class Meta:
        model = Task
        fields = ("event", "role")


class PersonSerializerAllData(PersonSerializer):
    badges = BadgeSerializer(many=True, read_only=True)  # type: ignore
    awards = AwardSerializerExpandEvent(many=True, read_only=True, source="award_set")  # type: ignore
    tasks = TaskSerializerNoPerson(many=True, read_only=True, source="task_set")  # type: ignore
    languages = serializers.SlugRelatedField[Language](many=True, read_only=True, slug_field="name")
    training_requests = TrainingRequestSerializer(many=True, read_only=True, source="trainingrequest_set")
    training_progresses = TrainingProgressSerializer(many=True, read_only=True, source="trainingprogress_set")
    consents = serializers.SerializerMethodField("get_consents")  # type: ignore

    class Meta:
        model = Person
        fields = (
            "username",
            "personal",
            "middle",
            "family",
            "email",
            "secondary_email",
            "gender",
            "gender_other",
            "airport_iata",
            "country",
            "timezone",
            "github",
            "twitter",
            "bluesky",
            "mastodon",
            "url",
            "orcid",
            "affiliation",
            "occupation",
            "user_notes",
            "badges",
            "lessons",
            "languages",
            "domains",
            "awards",
            "tasks",
            "training_requests",
            "training_progresses",
            "consents",
        )

    def get_consents(self, person: Person) -> dict[str, Any]:
        queryset = Consent.objects.filter(person=person).active()
        serializer = ConsentSerializer(instance=queryset, many=True)
        return serializer.data


class CommunityRoleConfigSerializer(serializers.ModelSerializer[CommunityRoleConfig]):
    class Meta:
        model = CommunityRoleConfig
        fields = [
            "id",
            "created_at",
            "last_updated_at",
            "name",
            "display_name",
            "link_to_award",
            "award_badge_limit",
            "autoassign_when_award_created",
            "link_to_membership",
            "additional_url",
            "generic_relation_content_type",
        ]


class InstructorRecruitmentSerializer(serializers.ModelSerializer[InstructorRecruitment]):
    class Meta:
        model = InstructorRecruitment
        fields = [
            "id",
            "created_at",
            "last_updated_at",
            "assigned_to",
            "status",
            "notes",
            "event",
        ]
