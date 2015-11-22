import datetime
import json
from unittest.mock import patch

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.views import (
    ExportBadgesView,
    ExportInstructorLocationsView,
    ExportMembersView,
)
from workshops.models import (
    Badge,
    Award,
    Person,
    Airport,
    Role
)
from workshops.util import universal_date_format


class TestExportingBadges(APITestCase):
    def setUp(self):
        # set up two badges, one with users, one without any
        self.badge1 = Badge.objects.create(name='badge1', title='Badge1',
                                           criteria='')
        self.badge2 = Badge.objects.create(name='badge2', title='Badge2',
                                           criteria='')
        self.user1 = Person.objects.create_user('user1', 'User1', 'Name',
                                                'user1@name.org')
        self.user2 = Person.objects.create_user('user2', 'User2', 'Name',
                                                'user2@name.org')
        Award.objects.create(person=self.user1, badge=self.badge1,
                             awarded=datetime.date.today())
        Award.objects.create(person=self.user2, badge=self.badge1,
                             awarded=datetime.date.today())

        # make sure we *do* get empty badges
        self.expecting = [
            {
                'name': 'badge1',
                'persons': [
                    {'name': 'User1 Name', 'user': 'user1'},
                    {'name': 'User2 Name', 'user': 'user2'},
                ]
            },
            {
                'name': 'badge2',
                'persons': [],
            },
        ]

    def test_serialization(self):
        view = ExportBadgesView()
        serializer = view.get_serializer_class()
        response = serializer(view.get_queryset(), many=True)
        self.assertEqual(response.data, self.expecting)

    def test_view(self):
        # test only JSON output
        url = reverse('api:export-badges')
        response = self.client.get(url, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)


class TestExportingInstructors(APITestCase):
    def setUp(self):
        # set up two badges, one with users, one without any
        self.badge = Badge.objects.create(name='instructor',
                                          title='Instructor',
                                          criteria='')
        self.airport1 = Airport.objects.create(
            iata='ABC', fullname='Airport1', country='PL', latitude=1,
            longitude=2,
        )
        self.airport2 = Airport.objects.create(
            iata='ABD', fullname='Airport2', country='US', latitude=2,
            longitude=1,
        )
        self.user1 = Person.objects.create(
            username='user1', personal='User1', family='Name',
            email='user1@name.org', airport=self.airport1,
        )
        self.user2 = Person.objects.create(
            username='user2', personal='User2', family='Name',
            email='user2@name.org', airport=self.airport1,
        )
        Award.objects.create(person=self.user1, badge=self.badge,
                             awarded=datetime.date.today())
        Award.objects.create(person=self.user2, badge=self.badge,
                             awarded=datetime.date.today())

        # make sure we *do not* get empty airports
        self.expecting = [
            {
                'name': 'Airport1',
                'country': 'PL',
                'latitude': 1.0,
                'longitude': 2.0,
                'instructors': [
                    {'name': 'User1 Name', 'user': 'user1'},
                    {'name': 'User2 Name', 'user': 'user2'},
                ]
            },
        ]

    def test_serialization(self):
        view = ExportInstructorLocationsView()
        serializer = view.get_serializer_class()
        response = serializer(view.get_queryset(), many=True)
        self.assertEqual(response.data, self.expecting)

    def test_view(self):
        # test only JSON output
        url = reverse('api:export-instructors')
        response = self.client.get(url, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)


class TestExportingMembers(APITestCase):
    def setUp(self):
        # Note: must create instructor badge for get_members query to run.
        # Same for instructor role
        Badge.objects.create(name='instructor', title='Instructor',
                             criteria='')
        Role.objects.create(name='instructor')

        self.spiderman = Person.objects.create(
            personal='Peter', middle='Q.', family='Parker',
            email='peter@webslinger.net',
            username="spiderman")

        self.member = Badge.objects.create(name='member',
                                           title='Member',
                                           criteria='')

        Award.objects.create(person=self.spiderman,
                             badge=self.member,
                             awarded=datetime.date(2014, 1, 1))

        self.expecting = [
            {
                'name': 'Peter Q. Parker',
                'email': 'peter@webslinger.net'
            },
        ]

    @patch.object(ExportMembersView, 'request', query_params={}, create=True)
    def test_serialization(self, mock_request):
        # we're mocking a request here because it's not possible to create
        # a fake request context for the view
        view = ExportMembersView()
        serializer = view.get_serializer_class()
        response = serializer(view.get_queryset(), many=True)
        self.assertEqual(response.data, self.expecting)

    def test_view_default_cutoffs(self):
        # test only JSON output
        url = reverse('api:export-members')
        response = self.client.get(url, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)

    def test_view_explicit_earliest(self):
        url = reverse('api:export-members')
        data = {'earliest': universal_date_format(datetime.date.today())}

        response = self.client.get(url, data, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)
