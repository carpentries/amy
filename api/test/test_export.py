import datetime
import json
from unittest.mock import patch

from django.core.urlresolvers import reverse
from rest_framework import status

from api.test.base import APITestBase
from api.views import (
    ExportBadgesView,
    ExportBadgesByPersonView,
    ExportInstructorLocationsView,
    ExportMembersView,
)
from workshops.models import (
    Badge,
    Award,
    Person,
    Airport,
    Role,
)
from workshops.util import universal_date_format


class BaseExportingTest(APITestBase):
    def setUp(self):
        # remove all existing badges (this will be rolled back anyway)
        # including swc-instructor and dc-instructor introduced by migration
        # 0064
        Badge.objects.all().delete()

    def login(self):
        self.admin = Person.objects.create_superuser(
                username="admin", personal="Super", family="User",
                email="sudo@example.org", password='admin')
        self.client.login(username='admin', password='admin')


class TestExportingBadges(BaseExportingTest):
    def setUp(self):
        super().setUp()

        today = datetime.date.today()

        # set up two badges, one with users, one without any
        self.badge1 = Badge.objects.create(name='badge1', title='Badge1',
                                           criteria='')
        self.badge2 = Badge.objects.create(name='badge2', title='Badge2',
                                           criteria='')
        self.user1 = Person.objects.create_user(
            username='user1', email='user1@name.org',
            personal='User1', family='Name')
        self.user2 = Person.objects.create_user(
            username='user2', email='user2@name.org',
            personal='User2', family='Name')
        Award.objects.create(person=self.user1, badge=self.badge1,
                             awarded=today)
        Award.objects.create(person=self.user2, badge=self.badge1,
                             awarded=today)

        # make sure we *do* get empty badges
        self.expecting = [
            {
                'name': 'badge1',
                'persons': [
                    {'name': 'User1 Name', 'user': 'user1',
                     'awarded': '{:%Y-%m-%d}'.format(today)},
                    {'name': 'User2 Name', 'user': 'user2',
                     'awarded': '{:%Y-%m-%d}'.format(today)},
                ],
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


class TestExportingBadgesByPerson(BaseExportingTest):
    def setUp(self):
        super().setUp()

        today = datetime.date.today()

        # set up two users one with badges, one without any
        self.user1 = Person.objects.create_user(
            username='user1', email='user1@name.org',
            personal='User1', family='Name')
        self.user2 = Person.objects.create_user(
            username='user2', email='user2@name.org',
            personal='User2', family='Name')
        self.badge1 = Badge.objects.create(name='badge1', title='Badge1',
                                           criteria='')
        self.badge2 = Badge.objects.create(name='badge2', title='Badge2',
                                           criteria='')
        Award.objects.create(person=self.user1, badge=self.badge1,
                             awarded=today)
        Award.objects.create(person=self.user1, badge=self.badge2,
                             awarded=today)

        # make sure we *do* get users without badges
        self.expecting = [
            {
                'username': 'user1',
                'email': 'user1@name.org',
                'personal': 'User1',
                'middle': '',
                'family': 'Name',
                'badges': [
                    {
                        'name': 'badge1',
                        'title': 'Badge1',
                        'criteria': '',
                    },
                    {
                        'name': 'badge2',
                        'title': 'Badge2',
                        'criteria': '',
                    },
                ],
            },
        ]

    def test_serialization(self):
        view = ExportBadgesByPersonView()
        serializer = view.get_serializer_class()
        response = serializer(view.get_queryset(), many=True)
        self.assertEqual(response.data, self.expecting)

    def test_view(self):
        # test only JSON output
        url = reverse('api:export-badges-by-person')
        response = self.client.get(url, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)


class TestExportingInstructors(BaseExportingTest):
    def setUp(self):
        super().setUp()

        # set up two badges, one for each user
        self.swc_instructor = Badge.objects.create(
            name='swc-instructor', title='Software Carpentry Instructor',
            criteria='')
        self.dc_instructor = Badge.objects.create(
            name='dc-instructor', title='Data Carpentry Instructor',
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
        # user1 is only a SWC instructor
        Award.objects.create(person=self.user1, badge=self.swc_instructor,
                             awarded=datetime.date.today())
        # user2 is only a DC instructor
        Award.objects.create(person=self.user2, badge=self.dc_instructor,
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


class TestExportingMembers(BaseExportingTest):
    def setUp(self):
        super().setUp()

        # Note: must create instructor badges for get_members query to run.
        # Same for instructor role
        Badge.objects.create(
            name='swc-instructor', title='Software Carpentry Instructor',
            criteria='')
        Badge.objects.create(
            name='dc-instructor', title='Data Carpentry Instructor',
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
                'email': 'peter@webslinger.net',
                'username': 'spiderman',
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

    def test_requires_login(self):
        url = reverse('api:export-members')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.login()
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_view_default_cutoffs(self):
        # test only JSON output
        url = reverse('api:export-members')
        self.login()
        response = self.client.get(url, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)

    def test_view_explicit_earliest(self):
        url = reverse('api:export-members')
        data = {'earliest': universal_date_format(datetime.date.today())}

        self.login()
        response = self.client.get(url, data, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)
