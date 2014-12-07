from django.test import TestCase
from ..models import Event
from mock import patch
from datetime import date

class FakeDate(date):
    "A fake replacement for date that can be mocked for testing."
    pass

    @classmethod
    def today(cls):
        return cls(2013, 12, 7)

@patch('workshops.models.datetime.date', FakeDate)
class TestEvent(TestCase):
    "Tests for the event model and it's manager"

    fixtures = ['event_test']

    def test_get_future_events(self):
        """Test that the events manager can find upcoming events"""

        upcoming_events = Event.objects.upcoming_events()

        # There are 2 upcoming events
        assert len(upcoming_events) == 2

        # They should all start with upcoming
        assert all([e.slug[:8] == 'upcoming' for e in upcoming_events])


    def test_get_past_events(self):
        """Test that the events manager can find past events"""

        past_events = Event.objects.past_events()

        # There are 3 past events
        assert len(past_events) == 3

        # They should all start with past
        assert all([e.slug[:4] == 'past' for e in past_events])


    def test_get_ongoing_events(self):
        """Test the events manager can find all events overlapping today.

        Include events that (according to the timestamp) are not ongoing,
        but which started or finished today.
        """

        ongoing_events = Event.objects.ongoing_events()

        event_slugs = [e.slug for e in ongoing_events]

        correct_slugs = ['started_today',
                         'currently_running',
                         'ends_today',]

        self.assertItemsEqual(event_slugs, correct_slugs)
