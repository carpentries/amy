import datetime
import json
from unittest.mock import MagicMock

from django.http import QueryDict
from django.urls import reverse
from rest_framework import status

from api.test.base import APITestBase
from api.views import (
    ReportsViewSet,
)
from workshops.models import (
    Badge,
    Award,
    Person,
    Role,
    Organization,
    Task,
    Event,
)
from workshops.test.base import TestBase


class BaseReportingTest(APITestBase):

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
        host = Organization.objects.create(domain='host.edu', fullname='Organization EDU')
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
        Award.objects.create(person=instructor, badge=swc_instructor)
        # Award a DC Badge
        Award.objects.create(person=instructor, badge=dc_instructor)

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


class TestCSVYAMLListSerialization(BaseReportingTest):
    def setUp(self):
        self.iterable = zip(['list', 'dict', 'tuple'],
                            ['set', 'namedtuple', 'OrderedDict'])
        self.formats = ReportsViewSet.formats_requiring_lists

    def test_listify_query_param(self):
        """Regression test: make sure it's possible to iterate through results
        serialized with CSV or YAML serializer.

        This test uses `?format' query param."""
        rvs = ReportsViewSet()
        for format_ in self.formats:
            with self.subTest(format=format_):
                mock_request = MagicMock()
                mock_request.query_params = QueryDict('format={}'
                                                      .format(format_))
                result = rvs.listify(self.iterable, mock_request)
                self.assertEqual(type(result), type(list()))

    def test_listify_format_as_param(self):
        """Regression test: make sure it's possible to iterate through results
        serialized with CSV or YAML serializer.

        This test uses 'format' function parameter."""
        rvs = ReportsViewSet()
        for format_ in self.formats:
            with self.subTest(format=format_):
                mock_request = MagicMock()
                mock_request.query_params = QueryDict()
                result = rvs.listify(self.iterable, mock_request,
                                     format=format_)
                self.assertEqual(type(result), type(list()))

    def test_iterator_when_not_forbidden_format(self):
        """Ensure other formats than self.formats return iterators/generators,
        not lists."""
        format_ = 'json'
        self.assertNotIn(format_, self.formats)

        rvs = ReportsViewSet()
        mock_request = MagicMock()
        mock_request.query_params = QueryDict()
        result = rvs.listify(self.iterable, mock_request,
                             format=format_)
        self.assertNotEqual(type(result), type(list()))

    def test_embedded_iterator_listified(self):
        """Regression: test if advanced structure, generated e.g. by
        `all_activity_over_time` report, doesn't raise RepresenterError when
        used with YAML renderer."""
        t = TestBase()
        t.setUp()
        t._setUpTags()

        format_ = 'yaml'
        self.assertIn(format_, self.formats)

        rvs = ReportsViewSet()
        mock_request = MagicMock()
        mock_request.query_params = QueryDict()
        data = rvs.all_activity_over_time(mock_request, format=format_).data
        self.assertEqual(type(data['missing']['attendance']), type([]))
        self.assertEqual(type(data['missing']['instructors']), type([]))


class TestNotCountingInstructorsTwice(BaseReportingTest):
    def setUp(self):
        super().setUp()

        # Get instructor badges
        swc_instructor, _ = Badge.objects.get_or_create(name='swc-instructor')
        dc_instructor, _ = Badge.objects.get_or_create(name='dc-instructor')

        # Create instructors
        instructor = Person.objects.create(
            username='harrypotter', personal='Harry', family='Potter',
            email='user1@name.org',
        )
        another_instructor = Person.objects.create(
            username='bobsmith', personal='Bob', family='Smith',
            email='bob.smith@name.org',
        )

        # Award badges (harrypotter is a double-instructor)
        Award.objects.create(person=instructor, badge=swc_instructor,
                             awarded=datetime.date(2016, 10, 3))
        Award.objects.create(person=instructor, badge=dc_instructor,
                             awarded=datetime.date(2016, 10, 2))
        Award.objects.create(person=another_instructor, badge=dc_instructor,
                             awarded=datetime.date(2016, 10, 4))

    def test_instructors_over_time(self):
        """Make sure we don't count double-instructor twice. Regression against
        #978."""
        url = reverse('api:reports-instructors-over-time')
        response = self.client.get(url, {'format': 'json'})
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), [
            {'count': 1, 'date': '2016-10-02'},
            {'count': 2, 'date': '2016-10-04'},
        ])
