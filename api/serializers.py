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
        fields = ('name', 'latitude', 'longitude', 'instructors', 'country')


class EventSerializer(serializers.ModelSerializer):
    humandate = serializers.SerializerMethodField()
    country = serializers.CharField()
    start = serializers.DateField(format=None)
    end = serializers.DateField(format=None)
    url = serializers.URLField(source='website_url')
    eventbrite_id = serializers.CharField(source='reg_key')

    def get_humandate(self, obj):
        """Render start and end dates as human-readable short date."""
        return EventSerializer.human_readable_date(obj.start, obj.end)

    @staticmethod
    def human_readable_date(date1, date2):
        """Render start and end dates as human-readable short date."""
        if date1 and not date2:
            return '{:%b %d, %Y}-???'.format(date1)
        elif date2 and not date1:
            return '???-{:%b %d, %Y}'.format(date2)
        elif not date2 and not date1:
            return '???-???'

        if date1.year == date2.year:
            if date1.month == date2.month:
                return '{:%b %d}-{:%d, %Y}'.format(date1, date2)
            else:
                return '{:%b %d}-{:%b %d, %Y}'.format(date1, date2)
        else:
            return '{:%b %d, %Y}-{:%b %d, %Y}'.format(date1, date2)

    class Meta:
        model = Event
        fields = (
            'slug', 'start', 'end', 'url', 'humandate', 'contact', 'country',
            'venue', 'address', 'latitude', 'longitude', 'eventbrite_id',
        )
