from rest_framework import serializers

from workshops.models import (
    Badge,
    Airport,
    Person,
    Event,
    TodoItem,
    Tag,
    Organization,
    Task,
    Award,
    TrainingRequest,
    TrainingRequirement,
    TrainingProgress,
)


class AwardPersonSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='person.full_name')
    user = serializers.CharField(source='person.username')

    class Meta:
        model = Award
        fields = ('name', 'user', 'awarded')


class PersonUsernameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name')
    user = serializers.CharField(source='username')

    class Meta:
        model = Person
        fields = ('name', 'user', )


class PersonNameEmailUsernameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name')

    class Meta:
        model = Person
        fields = ('name', 'email', 'username')


class PersonNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name')

    class Meta:
        model = Person
        fields = ('name', )


class ExportBadgesSerializer(serializers.ModelSerializer):
    persons = AwardPersonSerializer(many=True, source='award_set')

    class Meta:
        model = Badge
        fields = ('name', 'persons')


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ('name', 'title', 'criteria')


class ExportBadgesByPersonSerializer(serializers.ModelSerializer):
    badges = BadgeSerializer(many=True)
    class Meta:
        model = Person
        fields = ('username', 'personal', 'middle', 'family', 'email',
                  'badges')


class ExportInstructorLocationsSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='fullname')
    instructors = PersonUsernameSerializer(many=True,
                                           source='public_instructor_set')

    class Meta:
        model = Airport
        fields = ('name', 'latitude', 'longitude', 'instructors', 'country')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('name', )


class ExportEventSerializer(serializers.ModelSerializer):
    humandate = serializers.CharField(source='human_readable_date')
    country = serializers.CharField()
    start = serializers.DateField(format=None)
    end = serializers.DateField(format=None)
    url = serializers.URLField(source='website_url')
    eventbrite_id = serializers.CharField(source='reg_key')
    tags = TagSerializer(many=True)

    class Meta:
        model = Event
        fields = (
            'slug', 'start', 'end', 'url', 'humandate', 'contact', 'country',
            'venue', 'address', 'latitude', 'longitude', 'eventbrite_id',
            'tags',
        )


class TimelineTodoSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    start = serializers.DateField(format=None, source='due')

    class Meta:
        model = TodoItem
        fields = (
            'content', 'start',
        )

    def get_content(self, obj):
        """Return HTML containing interesting information for admins.  This
        will be displayed on labels in the timeline."""

        return '<a href="{url}">{event}</a><br><small>{todo}</small>'.format(
            url=obj.event.get_absolute_url(),
            event=obj.event.slug,
            todo=obj.title,
        )


class WorkshopsOverTimeSerializer(serializers.Serializer):
    date = serializers.DateField(format=None, source='start')
    count = serializers.IntegerField()


class InstructorsOverTimeSerializer(serializers.Serializer):
    date = serializers.DateField(format=None)
    count = serializers.IntegerField()


class InstructorNumTaughtSerializer(serializers.Serializer):
    person = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:person-detail', lookup_field='pk',
        source='*')
    name = serializers.CharField(source='full_name')
    num_taught = serializers.IntegerField()


class InstructorsByTimePeriodSerializer(serializers.ModelSerializer):
    event_slug = serializers.CharField(source='event.slug')
    person_name = serializers.CharField(source='person.full_name')
    person_email = serializers.EmailField(source='person.email')
    num_taught = serializers.IntegerField()

    class Meta:
        model = Task
        fields = ('event_slug', 'person_name', 'person_email', 'num_taught', )


# ----------------------
# "new" API starts below
# ----------------------


class OrganizationSerializer(serializers.ModelSerializer):
    country = serializers.CharField()

    class Meta:
        model = Organization
        fields = ('domain', 'fullname', 'country', 'notes')


class AirportSerializer(serializers.ModelSerializer):
    country = serializers.CharField()

    class Meta:
        model = Airport
        fields = ('iata', 'fullname', 'country', 'latitude', 'longitude')


class AwardSerializer(serializers.ModelSerializer):
    badge = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field='name')
    event = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:event-detail', lookup_field='slug')

    class Meta:
        model = Award
        fields = ('badge', 'awarded', 'event')


class PersonSerializer(serializers.ModelSerializer):
    airport = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:airport-detail', lookup_field='iata')
    country = serializers.CharField()
    lessons = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name')
    domains = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name')
    badges = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name')
    awards = serializers.HyperlinkedIdentityField(
        view_name='api:person-awards-list',
        lookup_field='pk',
        lookup_url_kwarg='person_pk',
    )
    tasks = serializers.HyperlinkedIdentityField(
        view_name='api:person-tasks-list',
        lookup_field='pk',
        lookup_url_kwarg='person_pk',
    )

    class Meta:
        model = Person
        fields = (
            'personal', 'middle', 'family', 'email', 'gender', 'may_contact',
            'publish_profile', 'airport', 'country',
            'github', 'twitter', 'url', 'orcid', 'username', 'notes',
            'affiliation', 'badges', 'lessons', 'domains', 'awards', 'tasks',
        )


class TaskSerializer(serializers.ModelSerializer):
    event = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:event-detail', lookup_field='slug')
    person = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:person-detail')
    role = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field='name')

    class Meta:
        model = Task
        fields = ('event', 'person', 'role')


class TodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodoItem
        fields = ('completed', 'title', 'due', 'additional')


class EventSerializer(serializers.ModelSerializer):
    country = serializers.CharField()
    start = serializers.DateField(format=None)
    end = serializers.DateField(format=None)

    host = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:organization-detail', lookup_field='domain')
    administrator = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:organization-detail', lookup_field='domain')
    tags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name')
    tasks = serializers.HyperlinkedIdentityField(
        view_name='api:event-tasks-list',
        lookup_field='slug',
        lookup_url_kwarg='event_slug',
    )
    todos = serializers.HyperlinkedIdentityField(
        view_name='api:event-todos-list',
        lookup_field='slug',
        lookup_url_kwarg='event_slug',
        source='todoitem_set',
    )
    assigned_to = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:person-detail')

    class Meta:
        model = Event
        fields = (
            'slug', 'completed', 'start', 'end', 'host', 'administrator',
            'tags', 'website_url', 'reg_key', 'admin_fee', 'invoice_status',
            'attendance', 'contact', 'country', 'venue', 'address',
            'latitude', 'longitude', 'notes', 'tasks', 'todos', 'assigned_to',
        )


class TrainingRequestSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='get_state_display')
    domains = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name')
    previous_involvement = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name')
    previous_training = serializers.CharField(
        source='get_previous_training_display')
    previous_experience = serializers.CharField(
        source='get_previous_experience_display')
    programming_language_usage_frequency = serializers.CharField(
        source='get_programming_language_usage_frequency_display')
    teaching_frequency_expectation = serializers.CharField(
        source='get_teaching_frequency_expectation_display')
    max_travelling_frequency = serializers.CharField(
        source='get_max_travelling_frequency_display')

    class Meta:
        model = TrainingRequest
        fields = (
            'created_at', 'last_updated_at',
            'state', 'group_name', 'personal', 'middle', 'family', 'email',
            'github', 'occupation', 'occupation_other', 'affiliation',
            'location', 'country', 'underresourced', 'underrepresented',
            'domains', 'domains_other', 'nonprofit_teaching_experience',
            'previous_involvement', 'previous_training',
            'previous_training_other', 'previous_training_explanation',
            'previous_experience', 'previous_experience_other',
            'previous_experience_explanation',
            'programming_language_usage_frequency',
            'teaching_frequency_expectation',
            'teaching_frequency_expectation_other',
            'max_travelling_frequency', 'max_travelling_frequency_other',
            'reason', 'comment',
            'training_completion_agreement', 'workshop_teaching_agreement',
            'data_privacy_agreement', 'code_of_conduct_agreement',
        )


class TrainingRequestWithPersonSerializer(TrainingRequestSerializer):
    person = serializers.SlugRelatedField(many=False, read_only=True,
                                          slug_field='full_name')
    person_id = serializers.PrimaryKeyRelatedField(many=False, read_only=True,
                                                   source='person')
    domains = serializers.SerializerMethodField()
    previous_involvement = serializers.SerializerMethodField()
    awards = serializers.SerializerMethodField()
    training_tasks = serializers.SerializerMethodField()

    def get_domains(self, obj):
        return ", ".join(map(lambda x: getattr(x, 'name'),
                             obj.domains.all()))

    def get_previous_involvement(self, obj):
        return ", ".join(map(lambda x: getattr(x, 'name'),
                             obj.previous_involvement.all()))

    def get_awards(self, obj):
        if obj.person:
            return ", ".join(
                map(
                    lambda x: "{} {:%Y-%m-%d}".format(x.badge.name, x.awarded),
                              obj.person.award_set.all()
                )
            )
        else:
            return ""

    def get_training_tasks(self, obj):
        if obj.person:
            return ", ".join(
                map(lambda x: x.event.slug, obj.person.task_set.all())
            )
        else:
            return ""

    class Meta:
        model = TrainingRequest
        fields = (
            'created_at', 'last_updated_at', 'state',
            'person', 'person_id', 'awards', 'training_tasks',
            'group_name', 'personal', 'middle', 'family',
            'email', 'github', 'underrepresented',
            'occupation', 'occupation_other', 'affiliation',
            'location', 'country', 'underresourced',
            'domains', 'domains_other', 'nonprofit_teaching_experience',
            'previous_involvement', 'previous_training',
            'previous_training_other', 'previous_training_explanation',
            'previous_experience', 'previous_experience_other',
            'previous_experience_explanation',
            'programming_language_usage_frequency',
            'teaching_frequency_expectation',
            'teaching_frequency_expectation_other',
            'max_travelling_frequency', 'max_travelling_frequency_other',
            'reason', 'comment',
            'training_completion_agreement', 'workshop_teaching_agreement',
            'data_privacy_agreement', 'code_of_conduct_agreement',
        )


class TrainingRequestForManualScoringSerializer(TrainingRequestSerializer):
    request_id = serializers.IntegerField(source='pk')

    class Meta:
        model = TrainingRequest
        fields = (
            'request_id',
            'score_manual',
            'score_notes',
            'group_name',
            'personal',
            'middle',
            'family',
            'underrepresented',
            'affiliation',
            'nonprofit_teaching_experience',
            'previous_training',
            'previous_training_other',
            'previous_training_explanation',
            'previous_experience',
            'previous_experience_other',
            'previous_experience_explanation',
            'teaching_frequency_expectation',
            'teaching_frequency_expectation_other',
            'max_travelling_frequency',
            'max_travelling_frequency_other',
            'reason',
            'comment',
        )


# The serializers below are meant to help display user's data without any
# links in relational fields; instead, either an expanded model is displayed,
# or - if it's simple enough - its' string representation.
# The serializers are used mostly in ExportPersonDataView.


class EventSerializerSimplified(EventSerializer):
    class Meta:
        model = Event
        fields = (
            'slug', 'start', 'end', 'tags', 'website_url', 'venue',
            'address', 'country', 'latitude', 'longitude',
        )


class AwardSerializerExpandEvent(AwardSerializer):
    event = EventSerializerSimplified(many=False, read_only=True)


class TrainingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRequirement
        fields = (
            'name', 'url_required', 'event_required',
        )


class TrainingProgressSerializer(serializers.ModelSerializer):
    requirement = TrainingRequirementSerializer(many=False, read_only=True)
    state = serializers.CharField(source='get_state_display')
    event = EventSerializerSimplified(many=False, read_only=True)
    evaluated_by = PersonNameSerializer(many=False, read_only=True)

    class Meta:
        model = TrainingProgress
        fields = (
            'created_at', 'last_updated_at',
            'requirement', 'state', 'discarded',
            'evaluated_by', 'event', 'url',
        )


class TaskSerializerNoPerson(TaskSerializer):
    event = EventSerializerSimplified(many=False, read_only=True)
    role = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field='name')

    class Meta:
        model = Task
        fields = ('event', 'role')


class PersonSerializerAllData(PersonSerializer):
    airport = AirportSerializer(many=False, read_only=True)
    badges = BadgeSerializer(many=True, read_only=True)
    awards = AwardSerializerExpandEvent(many=True, read_only=True, source='award_set')
    tasks = TaskSerializerNoPerson(many=True, read_only=True,
                                   source='task_set')
    languages = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name')
    training_requests = TrainingRequestSerializer(
        many=True, read_only=True, source='trainingrequest_set')
    training_progresses = TrainingProgressSerializer(
        many=True, read_only=True, source='trainingprogress_set')

    class Meta:
        model = Person
        fields = (
            'username', 'personal', 'middle', 'family', 'email', 'gender',
            'may_contact', 'publish_profile', 'airport',
            'github', 'twitter', 'url', 'affiliation',
            'user_notes', 'occupation', 'orcid',
            'data_privacy_agreement',
            'badges', 'lessons', 'languages', 'domains', 'awards', 'tasks',
            'training_requests', 'training_progresses',
        )
