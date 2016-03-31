from rest_framework import serializers

from workshops.models import (
    Badge,
    Airport,
    Person,
    Event,
    TodoItem,
    Tag,
    Host,
    Task,
    Award,
)


class AwardPersonSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='person.get_full_name')
    user = serializers.CharField(source='person.username')

    class Meta:
        model = Award
        fields = ('name', 'user', 'awarded')


class PersonUsernameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name')
    user = serializers.CharField(source='username')

    class Meta:
        model = Person
        fields = ('name', 'user', )


class PersonNameEmailUsernameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name')

    class Meta:
        model = Person
        fields = ('name', 'email', 'username')


class ExportBadgesSerializer(serializers.ModelSerializer):
    persons = AwardPersonSerializer(many=True, source='award_set')

    class Meta:
        model = Badge
        fields = ('name', 'persons')


class ExportInstructorLocationsSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='fullname')
    instructors = PersonUsernameSerializer(many=True, source='person_set')

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
            event=obj.event.get_ident(),
            todo=obj.title,
        )


class WorkshopsOverTimeSerializer(serializers.Serializer):
    date = serializers.DateField(format=None, source='start')
    count = serializers.IntegerField()


class InstructorsOverTimeSerializer(serializers.Serializer):
    date = serializers.DateField(format=None, source='awarded')
    count = serializers.IntegerField()


class InstructorNumTaughtSerializer(serializers.Serializer):
    person = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:person-detail', lookup_field='pk',
        source='*')
    name = serializers.CharField(source='get_full_name')
    num_taught = serializers.IntegerField()


class InstructorsByTimePeriodSerializer(serializers.ModelSerializer):
    event_slug = serializers.CharField(source='event.slug')
    person_name = serializers.CharField(source='person.get_full_name')
    person_email = serializers.EmailField(source='person.email')
    num_taught = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ('event_slug', 'person_name', 'person_email', 'num_taught')

    def get_num_taught(self, obj):
        """Count number of workshops attended with 'instructor' role."""
        # pretty terrible performance-wise, but we cannot annotate the original
        # query (yields wrong results)
        return obj.person.task_set.instructors().count()


# ----------------------
# "new" API starts below
# ----------------------


class HostSerializer(serializers.ModelSerializer):
    country = serializers.CharField()

    class Meta:
        model = Host
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
            'airport', 'github', 'twitter', 'url', 'username', 'notes',
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
        read_only=True, view_name='api:host-detail', lookup_field='domain')
    administrator = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:host-detail', lookup_field='domain')
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
