from rest_framework import serializers

from workshops.models import Badge, Airport, Person, Event


class PersonUsernameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name')
    user = serializers.CharField(source='username')

    class Meta:
        model = Person
        fields = ('name', 'user', )


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
        fields = ('name', 'latitude', 'longitude', 'instructors')


class EventSerializer(serializers.ModelSerializer):
    humandate = serializers.SerializerMethodField()
    country = serializers.CharField()

    def get_humandate(self, obj):
        """Render start and end dates as human-readable short date."""
        start = obj.start
        end = obj.end
        if start and not end:
            return '{:%b %d, %Y}-???'.format(start)
        elif end and not start:
            return '???-{:%b %d, %Y}'.format(end)
        elif not end and not start:
            return '???-???'

        if start.year == end.year:
            if start.month == end.month:
                return '{:%b %d}-{:%d, %Y}'.format(start, end)
            else:
                return '{:%b %d}-{:%b %d, %Y}'.format(start, end)
        else:
            return '{:%b %d, %Y}-{:%b %d, %Y}'.format(start, end)

    class Meta:
        model = Event
        fields = (
            'slug', 'start', 'end', 'url', 'humandate', 'contact', 'country',
            'venue', 'address', 'latitude', 'longitude',
        )
