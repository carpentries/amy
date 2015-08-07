from rest_framework import serializers

from workshops.models import Badge, Airport, Person


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
