import datetime
import json

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.views import (
    ExportBadgesView,
    ExportInstructorLocationsView,
)
from api.serializers import (
    ExportBadgesSerializer,
    ExportInstructorLocationsSerializer,
)
from workshops.models import (
    Badge,
    Award,
    Person,
    Airport,
)


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


def TestExportingMembers(APITestCase):
    def setUp(self):
        # FIXME: Why not super().setUp() ?

        self.host_alpha = Host.objects.create(domain='alpha.edu',
                                              fullname='Alpha Host',
                                              country='Azerbaijan',
                                              notes='')

        self.hermione = Person.objects.create(
            personal='Hermione', middle=None, family='Granger',
            email='hermione@granger.co.uk', gender='F', may_contact=True,
            airport=self.airport_0_0, github='herself', twitter='herself',
            url='http://hermione.org', username="granger.h")
        Award.objects.create(person=self.hermione,
                             badge=self.instructor,
                             awarded=datetime.date(2014, 1, 1))

        self.harry = Person.objects.create(
            personal='Harry', middle=None, family='Potter',
            email='harry@hogwarts.edu', gender='M', may_contact=True,
            airport=self.airport_0_50, github='hpotter', twitter=None,
            url=None, username="potter.h")
        Award.objects.create(person=self.harry,
                             badge=self.instructor,
                             awarded=datetime.date(2014, 5, 5))

        self.ron = Person.objects.create(
            personal='Ron', middle=None, family='Weasley',
            email='rweasley@ministry.gov.uk', gender='M', may_contact=False,
            airport=self.airport_50_100, github=None, twitter=None,
            url='http://geocities.com/ron_weas', username="weasley.ron")
        Award.objects.create(person=self.ron,
                             badge=self.instructor,
                             awarded=datetime.date(2014, 11, 11))

        self.spiderman = Person.objects.create(
            personal='Peter', middle='Q.', family='Parker',
            email='peter@webslinger.net', gender='O', may_contact=True,
            username="spiderman")

        one_day = datetime.timedelta(days=1)
        one_month = datetime.timedelta(days=30)
        three_years = datetime.timedelta(days=3 * 365)

        today = datetime.date.today()
        yesterday = today - one_day
        tomorrow = today + one_day
        
        earliest, latest = get_membership_cutoff()

        # Set up events in the past, at present, and in future.
        past = Event.objects.create(
            host=self.host_alpha,
            slug="in-past",
            start=today - three_years,
            end=tomorrow - three_years
        )

        present = Event.objects.create(
            host=self.host_alpha,
            slug="at-present",
            start=today,
            end=tomorrow
        )

        future = Event.objects.create(
            host=self.host_alpha,
            slug="in-future",
            start=today + one_month,
            end=tomorrow + one_month
        )

        # Roles and badges.
        instructor_role = Role.objects.create(name='instructor')
        member_badge = Badge.objects.create(name='member')

        # Spiderman is an explicit member.
        Award.objects.create(person=self.spiderman, badge=member_badge,
                             awarded=yesterday)

        # Hermione teaches in the past, now, and in future, so she's a member.
        Task.objects.create(event=past, person=self.hermione,
                            role=instructor_role)
        Task.objects.create(event=present, person=self.hermione,
                            role=instructor_role)
        Task.objects.create(event=future, person=self.hermione,
                            role=instructor_role)

        # Ron only teaches in the distant past, so he's not a member.
        t = \
        Task.objects.create(event=past, person=self.ron,
                            role=instructor_role)

        # Harry only teaches in the future, so he's not a member.
        Task.objects.create(event=future, person=self.harry,
                            role=instructor_role)

        self.expecting = [
            {
                'name': 'Hermione Granger',
                'email': 'hermione@granger.co.uk'
            },
            {
                'name': 'Harry Potter',
                'email': 'harry@hogwarts.edu'
            },
            {
                'name': 'Peter Q. Parker',
                'email': 'peter@webslinger.net'
            },
        ]

    def test_view(self):
        # test only JSON output
        url = reverse('api:export-members')
        response = self.client.get(url, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)
