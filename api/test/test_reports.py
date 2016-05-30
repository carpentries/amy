import datetime
import json

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.views import (
    ReportsViewSet,
)
from api.serializers import InstructorNumTaughtSerializer
from workshops.models import (
    Badge,
    Award,
    Person,
    Role,
    Host,
    Task,
    Event,
)


class BaseReportingTest(APITestCase):

    def setUp(self):
        self.login()

    def login(self):
        self.admin = Person.objects.create_superuser(
                username="admin", personal="Super", family="User",
                email="sudo@example.org", password='admin')
        self.client.login(username='admin', password='admin')


class TestReportingInstructorNumTaught(BaseReportingTest):
    def setUp(self):
        super().setUp()

        # get instructor badges
        swc_instructor, _ = Badge.objects.get_or_create(
            name='swc-instructor'
        )
        dc_instructor, _ = Badge.objects.get_or_create(
            name='dc-instructor'
        )
        # set up an event
        host = Host.objects.create(domain='host.edu', fullname='Host EDU')
        event = Event.objects.create(slug='event1', host=host)
        instructor = Person.objects.create(
            username='harrypotter', personal='Harry', family='Potter',
            email='user1@name.org',
        )
        instructor_role, _ = Role.objects.get_or_create(name='instructor')
        Task.objects.create(
            event=event,
            person=instructor,
            role=instructor_role
        )
        # Award a SWC Badge
        Award.objects.create(person=instructor, badge=swc_instructor,
                             awarded=datetime.date.today())
        # Award a DC Badge
        Award.objects.create(person=instructor, badge=dc_instructor,
                             awarded=datetime.date.today())

        # make sure we *do not* get twice the number expected
        self.expecting = [
            {
                'person': 'http://testserver/api/v1/persons/{}/?format=json'.format(
                    instructor.pk,
                ),
                'name': 'Harry Potter',
                'num_taught': 1,
            },
        ]

    def test_view(self):
        # test only JSON output
        url = reverse('api:reports-instructor-num-taught')
        response = self.client.get(url, {'format': 'json'})
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)
