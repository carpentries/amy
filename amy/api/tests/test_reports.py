import datetime
import json
from unittest.mock import MagicMock

from django.db.models import (
    IntegerField,
    Min,
    Value,
)
from django.http import QueryDict
from django.urls import reverse
from rest_framework import status

from api.filters import InstructorsOverTimeFilter
from api.tests.base import APITestBase
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
    Tag,
)
from workshops.tests.base import TestBase


class BaseReportingTest(APITestBase):

    def setUp(self):
        self.login()

    def login(self):
        self.admin = Person.objects.create_superuser(
                username="admin", personal="Super", family="User",
                email="sudo@example.org", password='admin')
        self.admin.data_privacy_agreement = True
        self.admin.save()
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
        lc_instructor, _ = Badge.objects.get_or_create(
            name='lc-instructor'
        )

        # prepare tags
        Tag.objects.bulk_create([
            Tag(name='TTT', details=''),
            Tag(name='LC', details=''),
            Tag(name='DC', details=''),
            Tag(name='SWC', details=''),
        ])

        # prepare an instructor
        instructor = Person.objects.create(
            username='harrypotter', personal='Harry', family='Potter',
            email='user1@name.org', country='GB',
        )

        # prepare instructor role
        instructor_role, _ = Role.objects.get_or_create(name='instructor')

        # create an organization host
        host = Organization.objects.create(domain='host.edu',
                                           fullname='Organization EDU')

        # set up events
        event1 = Event.objects.create(slug='event1', host=host)
        event2 = Event.objects.create(slug='event2', host=host)
        event2.tags.set(
            Tag.objects.filter(name__in=['SWC', 'DC', 'LC', 'TTT']))

        Task.objects.create(
            event=event1,
            person=instructor,
            role=instructor_role
        )
        Task.objects.create(
            event=event2,
            person=instructor,
            role=instructor_role
        )

        # Award a SWC, DC and LC badges
        Award.objects.create(person=instructor, badge=swc_instructor)
        Award.objects.create(person=instructor, badge=dc_instructor)
        Award.objects.create(person=instructor, badge=lc_instructor)

        # make sure we *do not* get twice the number expected
        self.expecting = [
            {
                'person': 'http://testserver/api/v1/persons/{}/?format=json'.format(
                    instructor.pk,
                ),
                'name': 'Harry Potter',
                'country': 'GB',
                'num_taught_SWC': 1,
                'num_taught_DC': 1,
                'num_taught_LC': 1,
                'num_taught_TTT': 1,
                'num_taught_total': 2,
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


class TestInstructorsOverTime(TestBase):

    def test_badge_non_iterable(self):
        """Regression test: ensure badges are correctly selected by filter."""
        badges = Badge.objects.instructor_badges()
        qs = Person.objects.annotate(
            date=Min('award__awarded'),
            count=Value(1, output_field=IntegerField())
        ).order_by('date')
        params = QueryDict("badges=1&badges=2")
        filter_ = InstructorsOverTimeFilter(params, queryset=qs)

        # would throw an error if the regression is still present
        self.assertTrue(filter_.qs)
