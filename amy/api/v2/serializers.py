from rest_framework import serializers

from emails.models import MAX_LENGTH, ScheduledEmail
from extrequests.models import SelfOrganisedSubmission
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import (
    Award,
    Event,
    Membership,
    Organization,
    Person,
    TagQuerySet,
    TrainingProgress,
    TrainingRequirement,
)


class AwardSerializer(serializers.ModelSerializer):
    person = serializers.SlugRelatedField(read_only=True, slug_field="username")
    badge = serializers.SlugRelatedField(read_only=True, slug_field="name")
    event = serializers.SlugRelatedField(read_only=True, slug_field="slug")
    awarded_by = serializers.SlugRelatedField(read_only=True, slug_field="username")

    class Meta:
        model = Award
        fields = (
            "pk",
            "person",
            "badge",
            "awarded",
            "event",
            "awarded_by",
        )


class OrganizationSerializer(serializers.ModelSerializer):
    country = serializers.CharField()
    affiliated_organizations = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="domain"
    )

    class Meta:
        model = Organization
        fields = (
            "pk",
            "domain",
            "fullname",
            "country",
            "latitude",
            "longitude",
            "affiliated_organizations",
        )


class EventSerializer(serializers.ModelSerializer):
    host = serializers.SlugRelatedField(read_only=True, slug_field="domain")
    sponsor = serializers.SlugRelatedField(read_only=True, slug_field="domain")
    membership = serializers.SlugRelatedField(read_only=True, slug_field="name")
    administrator = serializers.SlugRelatedField(read_only=True, slug_field="domain")
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    language = serializers.SlugRelatedField(read_only=True, slug_field="name")
    repository_url = serializers.URLField(read_only=True)
    website_url = serializers.URLField(read_only=True)
    # attendance = serializers.IntegerField()
    country = serializers.CharField()
    assigned_to = serializers.SlugRelatedField(read_only=True, slug_field="username")
    curricula = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="slug"
    )
    lessons = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    human_readable_date = serializers.CharField(read_only=True)
    eligible_for_instructor_recruitment = serializers.BooleanField(read_only=True)
    workshop_reports_link = serializers.CharField(read_only=True)
    main_tag = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            "pk",
            "slug",
            "completed",
            "start",
            "end",
            "host",
            "sponsor",
            "membership",
            "administrator",
            "tags",
            "language",
            "url",
            "repository_url",
            "website_url",
            "reg_key",
            # "attendance",
            "contact",
            "country",
            "venue",
            "address",
            "latitude",
            "longitude",
            "assigned_to",
            "open_TTT_applications",
            "curricula",
            "lessons",
            "public_status",
            "human_readable_date",
            "eligible_for_instructor_recruitment",
            "workshop_reports_link",
            "main_tag",
        )

    def get_main_tag(self, obj: Event) -> str | None:
        try:
            # Iterating like that is faster than using qs.filter(name__in=[...]).first()
            # because it doesn't introduce new queries.
            return next(
                tag.name
                for tag in obj.tags.all()
                if tag.name in TagQuerySet.CARPENTRIES_TAG_NAMES
            )
        except (IndexError, AttributeError, StopIteration):
            return None


class InstructorRecruitmentSignupSerializer(serializers.ModelSerializer):
    recruitment = serializers.PrimaryKeyRelatedField(read_only=True)
    event = serializers.CharField(read_only=True, source="recruitment.event.slug")
    person = serializers.SlugRelatedField(read_only=True, slug_field="username")

    class Meta:
        model = InstructorRecruitmentSignup
        fields = (
            "pk",
            "recruitment",
            "event",
            "person",
            "interest",
            "user_notes",
            "notes",
            "state",
            "created_at",
            "last_updated_at",
        )


class MembershipSerializer(serializers.ModelSerializer):
    # TODO: issue with intermediary model in M2M
    organizations = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="domain"
    )
    persons = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="username"
    )
    rolled_from_membership = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )
    rolled_to_membership = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )
    workshops_without_admin_fee_total_allowed = serializers.IntegerField()
    workshops_without_admin_fee_available = serializers.IntegerField()
    workshops_without_admin_fee_completed = serializers.IntegerField()
    workshops_without_admin_fee_planned = serializers.IntegerField()
    workshops_without_admin_fee_remaining = serializers.IntegerField()
    workshops_discounted_completed = serializers.IntegerField()
    workshops_discounted_planned = serializers.IntegerField()
    self_organized_workshops_completed = serializers.IntegerField()
    self_organized_workshops_planned = serializers.IntegerField()
    public_instructor_training_seats_total = serializers.IntegerField()
    public_instructor_training_seats_utilized = serializers.IntegerField()
    public_instructor_training_seats_remaining = serializers.IntegerField()
    inhouse_instructor_training_seats_total = serializers.IntegerField()
    inhouse_instructor_training_seats_utilized = serializers.IntegerField()
    inhouse_instructor_training_seats_remaining = serializers.IntegerField()
    cldt_seats_total = serializers.IntegerField()
    cldt_seats_utilized = serializers.IntegerField()
    cldt_seats_remaining = serializers.IntegerField()

    class Meta:
        model = Membership
        fields = (
            "pk",
            "name",
            "variant",
            "agreement_start",
            "agreement_end",
            "extensions",
            "contribution_type",
            "workshops_without_admin_fee_per_agreement",
            "workshops_without_admin_fee_rolled_from_previous",
            "workshops_without_admin_fee_rolled_over",
            "public_instructor_training_seats",
            "additional_public_instructor_training_seats",
            "public_instructor_training_seats_rolled_from_previous",
            "public_instructor_training_seats_rolled_over",
            "inhouse_instructor_training_seats",
            "additional_inhouse_instructor_training_seats",
            "inhouse_instructor_training_seats_rolled_from_previous",
            "inhouse_instructor_training_seats_rolled_over",
            "organizations",
            "registration_code",
            "agreement_link",
            "public_status",
            "emergency_contact",
            "consortium",
            "persons",
            "rolled_from_membership",
            "rolled_to_membership",
            "workshops_without_admin_fee_total_allowed",
            "workshops_without_admin_fee_available",
            "workshops_without_admin_fee_completed",
            "workshops_without_admin_fee_planned",
            "workshops_without_admin_fee_remaining",
            "workshops_discounted_completed",
            "workshops_discounted_planned",
            "self_organized_workshops_completed",
            "self_organized_workshops_planned",
            "public_instructor_training_seats_total",
            "public_instructor_training_seats_utilized",
            "public_instructor_training_seats_remaining",
            "inhouse_instructor_training_seats_total",
            "inhouse_instructor_training_seats_utilized",
            "inhouse_instructor_training_seats_remaining",
            "cldt_seats_total",
            "cldt_seats_utilized",
            "cldt_seats_remaining",
        )


class PersonSerializer(serializers.ModelSerializer):
    airport = serializers.SlugRelatedField(read_only=True, slug_field="iata")
    country = serializers.CharField()

    class Meta:
        model = Person
        fields = (
            "pk",
            "username",
            "personal",
            "middle",
            "family",
            "full_name",
            "email",
            "secondary_email",
            "country",
            "airport",
            "github",
            "twitter",
            "url",
            "user_notes",
            "affiliation",
            "is_active",
            "occupation",
            "orcid",
            "gender",
            "gender_other",
            "created_at",
            "last_updated_at",
            "archived_at",
        )


class ScheduledEmailSerializer(serializers.ModelSerializer):
    template = serializers.SlugRelatedField(read_only=True, slug_field="name")
    generic_relation_content_type = serializers.SlugRelatedField(
        read_only=True, slug_field="app_labeled_name"
    )

    class Meta:
        model = ScheduledEmail
        fields = (
            "pk",
            "state",
            "scheduled_at",
            "to_header",
            "to_header_context_json",
            "from_header",
            "reply_to_header",
            "cc_header",
            "bcc_header",
            "subject",
            "body",
            "context_json",
            "template",
            "generic_relation_content_type",
            "generic_relation_pk",
            "created_at",
            "last_updated_at",
        )


class ScheduledEmailLogDetailsSerializer(serializers.Serializer):
    details = serializers.CharField(max_length=MAX_LENGTH)


class TrainingProgressSerializer(serializers.ModelSerializer):
    trainee = serializers.SlugRelatedField(read_only=True, slug_field="username")
    requirement = serializers.SlugRelatedField(read_only=True, slug_field="name")
    involvement_type = serializers.SlugRelatedField(read_only=True, slug_field="name")
    event = serializers.SlugRelatedField(read_only=True, slug_field="slug")

    class Meta:
        model = TrainingProgress
        fields = (
            "pk",
            "trainee",
            "date",
            "requirement",
            "state",
            "involvement_type",
            "event",
            "url",
            "trainee_notes",
            "notes",
            "created_at",
            "last_updated_at",
        )


class TrainingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRequirement
        fields = (
            "pk",
            "name",
            "url_required",
            "event_required",
            "involvement_required",
        )


class SelfOrganisedSubmissionSerializer(serializers.ModelSerializer):
    event = serializers.SlugRelatedField(read_only=True, slug_field="slug")
    additional_contact = serializers.CharField()
    country = serializers.CharField()
    workshop_types = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )

    class Meta:
        model = SelfOrganisedSubmission
        fields = (
            "pk",
            "assigned_to",
            "state",
            "created_at",
            "last_updated_at",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
            "event",
            "personal",
            "family",
            "email",
            "institution",
            "institution_other_name",
            "institution_other_URL",
            "institution_department",
            "member_code",
            "online_inperson",
            "workshop_listed",
            "public_event",
            "public_event_other",
            "additional_contact",
            "start",
            "end",
            "workshop_url",
            "workshop_format",
            "workshop_format_other",
            "workshop_types",
            "workshop_types_other",
            "workshop_types_other_explain",
            "country",
            "language",
        )
