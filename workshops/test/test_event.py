from datetime import datetime, timedelta
import sys

from django.test import TestCase
from django.core.urlresolvers import reverse
from ..models import Event, Site


class TestEvent(TestCase):
    "Tests for the event model and it's manager"

    def setUp(self):

        # Create a test site
        test_site = Site.objects.create(domain='example.com',
                                        fullname='Test Site')

        # Create one new event for each day in the next 10 days
        for t in range(1, 11):
            event_start = datetime.now() + timedelta(days=t)
            Event.objects.create(start=event_start,
                                 slug='upcoming_{0}'.format(t),
                                 site=test_site,
                                 admin_fee=100)

        # Create one new event for each day from 10 days ago to
        # 3 days ago
        for t in range(3, 11):
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
                         'ends_today', ]

        if sys.version_info >= (3,):
            self.assertCountEqual(event_slugs, correct_slugs)
        else:
            self.assertItemsEqual(event_slugs, correct_slugs)


class TestEventViews(TestCase):
    "Tests for the event views"

    def setUp(self):

        # Create a test site
        test_site = Site.objects.create(domain='example.com',
                                        fullname='Test Site')

        # Create fifty new events
        for i in range(50):
            event_start = datetime.now()
            Event.objects.create(start=event_start,
                                 slug='test_event_{0}'.format(i),
                                 site=test_site,
                                 admin_fee=0)

    def test_events_view_paginated(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=10'
        response = self.client.get(events_url)

        # We asked for max 10 events, make sure we got them
        view_events = response.context['all_events']

        assert len(view_events) == 10

    def test_can_request_all_events(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=all'
        response = self.client.get(events_url)

        # We asked for all events, make sure we got them
        view_events = response.context['all_events']
        all_events = list(Event.objects.all())

        if sys.version_info >= (3,):
            self.assertCountEqual(view_events, all_events)
        else:
            self.assertItemsEqual(view_events, all_events)

    def test_invalid_items_per_page_gives_default_pagination(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=not_an_integer'
        response = self.client.get(events_url)

        # View should be paginated by default, so we shouldn't get all events
        view_events = response.context['all_events']

        assert len(view_events) < 50

    def test_non_integer_page_no_returns_first_page(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=10&page=not_an_integer'
        response = self.client.get(events_url)

        # Get the events for this page
        view_events = response.context['all_events']

        # They should still be paginated
        assert len(view_events) == 10

        # This should be the first page
        assert view_events.number == 1

    def test_page_no_too_large_returns_last_page(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=10&page=999'
        response = self.client.get(events_url)

        # Get the events for this page
        view_events = response.context['all_events']

        # They should still be paginated
        assert len(view_events) == 10

        # This should be the first page
        assert view_events.number == 5


class TestEventNotes(TestCase):
    """Make sure notes once written are saved forever!"""

    def setUp(self):
        # a test site is required for all new events
        self.test_site = Site.objects.create(domain='example.com',
                                             fullname='Test Site')

        # prepare a lifespan of all events
        self.event_start = datetime.now() + timedelta(days=-1)
        self.event_end = datetime.now() + timedelta(days=1)

    def test_event_without_notes(self):
        "Make sure event without notes don't have NULLed field ``notes``"
        e = Event(start=self.event_start,
                  end=self.event_end,
                  slug='no_notes',
                  site=self.test_site,
                  admin_fee=100)

        # test for field's default value (the field is not NULL)
        self.assertEqual(e.notes, "")  # therefore the field is not NULL

    def test_event_with_notes(self):
        "Make sure event with notes are correctly stored"

        notes = "This event's going to be extremely exhausting."

        e = Event(start=self.event_start,
                  end=self.event_end,
                  slug='with_notes',
                  site=self.test_site,
                  admin_fee=100,
                  notes=notes)

        # make sure that notes have been saved
        self.assertEqual(e.notes, notes)
