from django.test import TestCase
from ..models import Event, Site, Project
from datetime import datetime, timedelta

class TestEvent(TestCase):
    "Tests for the event model and it's manager"

    def setUp(self):

        # Create a test site
        test_site = Site.objects.create(domain='example.com',
                 fullname='Test Site')

        # Create a test project
        test_project = Project.objects.create(slug='test',
                       name='Test Project',
                       details='my test project')

        # Create one new event for each day in the next 10 days
        for t in range(1,11):
            event_start = datetime.now() + timedelta(days=t)
            Event.objects.create(start=event_start,
                                 slug='upcoming_{0}'.format(t),
                                 site=test_site,
                                 project=test_project,
                                 admin_fee=100)

        # Create one new event for each day from 10 days ago to
        # 3 days ago
        for t in range(3,11):
            event_start = datetime.now() + timedelta(days=-t)
            Event.objects.create(start=event_start,
                                 slug='past_{0}'.format(t),
                                 site=test_site,
                                 project=test_project,
                                 admin_fee=100)

        # Create an event that started yesterday and ends
        # tomorrow
        event_start = datetime.now() + timedelta(days=-1)
        event_end = datetime.now() + timedelta(days=1)
        Event.objects.create(start=event_start,
              end=event_end,
              slug='ends_tomorrow',
              site=test_site,
              project=test_project,
              admin_fee=100)

        # Create an event that ends today
        event_start = datetime.now() + timedelta(days=-1)
        event_end = datetime.now()
        Event.objects.create(start=event_start,
              end=event_end,
              slug='ends_today',
              site=test_site,
              project=test_project,
              admin_fee=100)

        # Create an event that starts today
        event_start = datetime.now()
        event_end = datetime.now() + timedelta(days=1)
        Event.objects.create(start=event_start,
              end=event_end,
              slug='starts_today',
              site=test_site,
              project=test_project,
              admin_fee=100)

    def test_get_future_events(self):
        """Test that the events manager can find upcoming events"""

        upcoming_events = Event.objects.upcoming_events()

        # There are 2 upcoming events
        assert len(upcoming_events) == 10

        # They should all start with upcoming
        assert all([e.slug[:8] == 'upcoming' for e in upcoming_events])


    def test_get_past_events(self):
        """Test that the events manager can find past events"""

        past_events = Event.objects.past_events()

        # There are 3 past events
        assert len(past_events) == 8

        # They should all start with past
        assert all([e.slug[:4] == 'past' for e in past_events])


    def test_get_ongoing_events(self):
        """Test the events manager can find all events overlapping today.

        Include events that (according to the timestamp) are not ongoing,
        but which started or finished today.
        """

        ongoing_events = Event.objects.ongoing_events()

        event_slugs = [e.slug for e in ongoing_events]

        correct_slugs = ['starts_today',
                         'ends_tomorrow',
                         'ends_today',]

        self.assertItemsEqual(event_slugs, correct_slugs)
