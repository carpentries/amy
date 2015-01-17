from django.core.urlresolvers import reverse
from django.test import TestCase
from ..models import Event, Site
from datetime import datetime, timedelta

class TestLandingPage(TestCase):
    "Tests for the workshop landing page"

    def setUp(self):

        # Create a test site
        test_site = Site.objects.create(domain='example.com',
                 fullname='Test Site')

        # Create one new event for each day in the next 10 days
        for t in range(1,11):
            event_start = datetime.now() + timedelta(days=t)
            Event.objects.create(start=event_start,
                                 slug='upcoming_{0}'.format(t),
                                 site=test_site,
                                 admin_fee=100)

        # Create one new event for each day from 10 days ago to
        # 3 days ago
        for t in range(3,11):
            event_start = datetime.now() + timedelta(days=-t)
            Event.objects.create(start=event_start,
                                 slug='past_{0}'.format(t),
                                 site=test_site,
                                 admin_fee=100)

        # Create an event that started yesterday and ends
        # tomorrow
        event_start = datetime.now() + timedelta(days=-1)
        event_end = datetime.now() + timedelta(days=1)
        Event.objects.create(start=event_start,
              end=event_end,
              slug='ends_tomorrow',
              site=test_site,
              admin_fee=100)

        # Create an event that ends today
        event_start = datetime.now() + timedelta(days=-1)
        event_end = datetime.now()
        Event.objects.create(start=event_start,
              end=event_end,
              slug='ends_today',
              site=test_site,
              admin_fee=100)

        # Create an event that starts today
        event_start = datetime.now()
        event_end = datetime.now() + timedelta(days=1)
        Event.objects.create(start=event_start,
              end=event_end,
              slug='starts_today',
              site=test_site,
              admin_fee=100)

    def test_has_upcoming_events(self):
        """Test that the landing page is passed some
        upcoming_events in the context.
        """

        response = self.client.get(reverse('index'))

        # This will fail if the context variable doesn't exist
        upcoming_events = response.context['upcoming_events']

        # There are 10 upcoming events
        assert len(upcoming_events) == 10

        # They should all start with upcoming
        assert all([e.slug[:8] == 'upcoming' for e in upcoming_events])
