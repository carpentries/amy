from rest_framework import serializers

from autoemails.models import EmailTemplate
from consents.models import Consent, Term
from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    Organization,
    Person,
    Task,
    TrainingProgress,
    TrainingRequest,
    TrainingRequirement,
)


class PersonNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name")

    class Meta:
        model = Person
        fields = ("name",)


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ("name", "title", "criteria")


# ----------------------
# "new" API starts below
# ----------------------


class OrganizationSerializer(serializers.ModelSerializer):
    country = serializers.CharField()

    class Meta:
        model = Organization
        fields = ("domain", "fullname", "country")


class AirportSerializer(serializers.ModelSerializer):
    country = serializers.CharField()

    class Meta:
        model = Airport
        fields = ("iata", "fullname", "country", "latitude", "longitude")


class AwardSerializer(serializers.ModelSerializer):
    badge = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")
    event = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:event-detail", lookup_field="slug"
    )

    class Meta:
        model = Award
        fields = ("badge", "awarded", "event")


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = ("slug", "content", "required_type", "help_text")


class ConsentSerializer(serializers.ModelSerializer):
    term = TermSerializer(read_only=True)
    term_option = serializers.StringRelatedField()

    class Meta:
        model = Consent
        fields = ("term", "term_option")


class PersonSerializer(serializers.ModelSerializer):
    airport = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:airport-detail", lookup_field="iata"
    )
    country = serializers.CharField()
    lessons = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    domains = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    badges = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    awards = serializers.HyperlinkedIdentityField(
        view_name="api:person-awards-list",
        lookup_field="pk",
        lookup_url_kwarg="person_pk",
    )
    tasks = serializers.HyperlinkedIdentityField(
        view_name="api:person-tasks-list",
        lookup_field="pk",
        lookup_url_kwarg="person_pk",
    )
    consents = serializers.HyperlinkedIdentityField(
        view_name="api:person-consents-list",
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
            "airport",
            "country",
            "github",
            "twitter",
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


class TaskSerializer(serializers.ModelSerializer):
    event = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:event-detail", lookup_field="slug"
    )
    person = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:person-detail"
    )
    role = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")

    class Meta:
        model = Task
        fields = ("event", "person", "role")


class EventSerializer(serializers.ModelSerializer):
    country = serializers.CharField()
    start = serializers.DateField(format=None)
    end = serializers.DateField(format=None)

    host = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:organization-detail", lookup_field="domain"
    )
    administrator = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:organization-detail", lookup_field="domain"
    )
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    tasks = serializers.HyperlinkedIdentityField(
        view_name="api:event-tasks-list",
        lookup_field="slug",
        lookup_url_kwarg="event_slug",
    )
    assigned_to = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:person-detail"
    )
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


class TrainingRequestSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source="get_state_display")
    domains = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    previous_involvement = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    previous_training = serializers.CharField(source="get_previous_training_display")
    previous_experience = serializers.CharField(
        source="get_previous_experience_display"
    )
    programming_language_usage_frequency = serializers.CharField(
        source="get_programming_language_usage_frequency_display"
    )
    teaching_frequency_expectation = serializers.CharField(
        source="get_teaching_frequency_expectation_display"
    )
    max_travelling_frequency = serializers.CharField(
        source="get_max_travelling_frequency_display"
    )

    class Meta:
        model = TrainingRequest
        fields = (
            "created_at",
            "last_updated_at",
            "state",
            "review_process",
            "group_name",
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
            "teaching_frequency_expectation",
            "teaching_frequency_expectation_other",
            "max_travelling_frequency",
            "max_travelling_frequency_other",
            "reason",
            "user_notes",
            "training_completion_agreement",
            "workshop_teaching_agreement",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
        )


class TrainingRequestWithPersonSerializer(TrainingRequestSerializer):
    person = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="full_name"
    )
    person_id = serializers.PrimaryKeyRelatedField(
        many=False, read_only=True, source="person"
    )
    domains = serializers.SerializerMethodField()
    previous_involvement = serializers.SerializerMethodField()
    awards = serializers.SerializerMethodField()
    training_tasks = serializers.SerializerMethodField()

    def get_domains(self, obj):
        return ", ".join(map(lambda x: getattr(x, "name"), obj.domains.all()))

    def get_previous_involvement(self, obj):
        return ", ".join(
            map(lambda x: getattr(x, "name"), obj.previous_involvement.all())
        )

    def get_awards(self, obj):
        if obj.person:
            return ", ".join(
                map(
                    lambda x: "{} {:%Y-%m-%d}".format(x.badge.name, x.awarded),
                    obj.person.award_set.all(),
                )
            )
        else:
            return ""

    def get_training_tasks(self, obj):
        if obj.person:
            return ", ".join(map(lambda x: x.event.slug, obj.person.training_tasks))
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
            "group_name",
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
            "teaching_frequency_expectation",
            "teaching_frequency_expectation_other",
            "max_travelling_frequency",
            "max_travelling_frequency_other",
            "reason",
            "user_notes",
            "training_completion_agreement",
            "workshop_teaching_agreement",
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
            "group_name",
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
    event = EventSerializerSimplified(many=False, read_only=True)


class TrainingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRequirement
        fields = (
            "name",
            "url_required",
            "event_required",
        )


class TrainingProgressSerializer(serializers.ModelSerializer):
    requirement = TrainingRequirementSerializer(many=False, read_only=True)
    state = serializers.CharField(source="get_state_display")
    event = EventSerializerSimplified(many=False, read_only=True)
    evaluated_by = PersonNameSerializer(many=False, read_only=True)

    class Meta:
        model = TrainingProgress
        fields = (
            "created_at",
            "last_updated_at",
            "requirement",
            "state",
            "discarded",
            "evaluated_by",
            "event",
            "url",
        )


class TaskSerializerNoPerson(TaskSerializer):
    event = EventSerializerSimplified(many=False, read_only=True)
    role = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")

    class Meta:
        model = Task
        fields = ("event", "role")


class PersonSerializerAllData(PersonSerializer):
    airport = AirportSerializer(many=False, read_only=True)
    badges = BadgeSerializer(many=True, read_only=True)
    awards = AwardSerializerExpandEvent(many=True, read_only=True, source="award_set")
    tasks = TaskSerializerNoPerson(many=True, read_only=True, source="task_set")
    languages = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    training_requests = TrainingRequestSerializer(
        many=True, read_only=True, source="trainingrequest_set"
    )
    training_progresses = TrainingProgressSerializer(
        many=True, read_only=True, source="trainingprogress_set"
    )
    consents = serializers.SerializerMethodField("get_consents")

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
            "airport",
            "country",
            "github",
            "twitter",
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

    def get_consents(self, person):
        queryset = Consent.objects.filter(person=person).active()
        serializer = ConsentSerializer(instance=queryset, many=True)
        return serializer.data


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            "id",
            "active",
            "created_at",
            "last_updated_at",
            "slug",
            "subject",
            "to_header",
            "from_header",
            "cc_header",
            "bcc_header",
            "reply_to_header",
            "body_template",
        ]
