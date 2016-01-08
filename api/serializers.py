from rest_framework import serializers

from workshops.models import Badge, Airport, Person, Event, TodoItem, Tag


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
    persons = PersonUsernameSerializer(many=True, source='person_set')

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


class EventSerializer(serializers.ModelSerializer):
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


class TodoSerializer(serializers.ModelSerializer):
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
