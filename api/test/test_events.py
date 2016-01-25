import datetime
import json
from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.http import QueryDict
from rest_framework import status
from rest_framework.test import APITestCase

from api.views import (
    PublishedEvents,
)
from workshops.models import (
    Event,
    Host,
)
from workshops.util import universal_date_format


class TestListingPublishedEvents(APITestCase):
    view = PublishedEvents
    serializer_class = PublishedEvents.serializer_class
    url = 'api:events-published'
    maxDiff = None

    def setUp(self):
        past = datetime.date(1993, 8, 30)
        today = datetime.date.today()
        future = datetime.date(2030, 3, 25)
        delta_2d = datetime.timedelta(days=2)
        delta_1d = datetime.timedelta(days=1)
        host = Host.objects.create(domain='host.edu', fullname='Host EDU')

        # past event
        self.event1 = Event.objects.create(
            slug='event1', start=past - delta_2d, end=past - delta_1d,
            host=host, latitude=3, longitude=-2, venue='University',
            address='On the street', country='US', contact='sb@sth.edu',
            url='https://user.github.io/repository/',
        )
        # ongoing event
        self.event2 = Event.objects.create(
            slug='event2', start=today - delta_2d, end=today + delta_2d,
            host=host, latitude=3, longitude=-2, venue='University',
            address='On the street', country='US', contact='sb@sth.edu',
            url='https://github.com/user/repository',
        )
        # future event
        self.event3 = Event.objects.create(
            slug='event3', start=future - delta_2d, end=future + delta_2d,
            host=host, latitude=3, longitude=-2, venue='University',
            address='On the street', country='US', contact='sb@sth.edu',
            url='http://github.com/user/repository/',
            reg_key='12341234',
        )
        # event with missing start
        self.event4 = Event.objects.create(
            slug='event4', end=past + delta_2d,
            host=host, latitude=3, longitude=-2, venue='University',
            address='On the street', country='US', contact='sb@sth.edu',
            url='http://url4/',
        )
        # event with missing URL
        self.event5 = Event.objects.create(
            slug='event5', start=future - delta_2d, end=future + delta_2d,
            host=host, latitude=3, longitude=-2, venue='University',
            address='On the street', country='US', contact='sb@sth.edu',
        )
        # event with missing country
        self.event6 = Event.objects.create(
            slug='event6', start=future - delta_2d, end=future + delta_2d,
            host=host, latitude=3, longitude=-2, venue='University',
            address='On the street', country=None, contact='sb@sth.edu',
            url='http://url6/',
        )
        # event with missing venue
        self.event7 = Event.objects.create(
            slug='event7', start=future - delta_2d, end=future + delta_2d,
            host=host, latitude=3, longitude=-2, venue='',
            address='On the street', country='US', contact='sb@sth.edu',
            url='http://url7/',
        )
        # event with missing both start and URL
        self.event8 = Event.objects.create(
            slug='event8', end=future + delta_1d,
            host=host, latitude=3.1, longitude=-1.9, venue='University',
            address='On the street', country='US', contact='sb@sth.edu',
        )
        # event with missing both country and venue
        self.event9 = Event.objects.create(
            slug='event9', start=future - delta_2d, end=future + delta_1d,
            host=host, latitude=3.1, longitude=-1.9, venue='',
            address='On the street', country=None, contact='sb@sth.edu',
            url='http://url9/',
        )
        # event with missing start, URL, country, and venue
        self.event10 = Event.objects.create(
            slug='event10', end=future + delta_1d,
            host=host, latitude=3.1, longitude=-1.9, venue='',
            address='On the street', country=None, contact='sb@sth.edu',
        )

        self.expecting = [
            {
                'slug': 'event3',
                'start': self.event3.start,
                'end': self.event3.end,
                'humandate': 'Mar 23-27, 2030',
                'latitude': 3.,
                'longitude': -2.,
                'venue': 'University',
                'address': 'On the street',
                'country': 'US',
                'url': 'https://user.github.io/repository/',
                'contact': 'sb@sth.edu',
                'eventbrite_id': '12341234',
                'tags': [],
            },
            {
                'slug': 'event2',
                'start': self.event2.start,
                'end': self.event2.end,
                'humandate': self.event2.human_readable_date,
                'latitude': 3.,
                'longitude': -2.,
                'venue': 'University',
                'address': 'On the street',
                'country': 'US',
                'url': 'https://user.github.io/repository/',
                'contact': 'sb@sth.edu',
                'eventbrite_id': None,
                'tags': [],
            },
            {
                'slug': 'event1',
                'start': self.event1.start,
                'end': self.event1.end,
                'humandate': 'Aug 28-29, 1993',
                'latitude': 3.,
                'longitude': -2.,
                'venue': 'University',
                'address': 'On the street',
                'country': 'US',
                'url': 'https://user.github.io/repository/',
                'contact': 'sb@sth.edu',
                'eventbrite_id': None,
                'tags': [],
            },
        ]

    @patch.object(PublishedEvents, 'request', query_params=QueryDict(),
                  create=True)
    def test_serialization(self, mock_request):
        # we're mocking a request here because it's not possible to create
        # a fake request context for the view
        response = self.serializer_class(self.view().get_queryset(), many=True)
        self.assertEqual(response.data, self.expecting)

    def test_view(self):
        # turn dates into strings for the sake of this test
        for i, event in enumerate(self.expecting):
            for date in ['start', 'end']:
                self.expecting[i][date] = universal_date_format(
                    self.expecting[i][date],
                )

        # test only JSON output
        url = reverse(self.url)
        response = self.client.get(url, format='json')
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(content), self.expecting)
