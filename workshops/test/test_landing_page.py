from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import patch
from datetime import date

class FakeDate(date):
    "A fake replacement for date that can be mocked for testing."
    pass

    @classmethod
    def today(cls):
        return cls(2013, 12, 7)

class TestLandingPage(TestCase):
    "Tests for the workshop landing page"

    fixtures = ['event_test']

    # We have to patch datetime.date.today so that all the test
    # fixture events have the right timing relative to today's
    # date - e.g. the "starts_today" event has a hard coded start
    # (2013/12/07), so we need to make sure django thinks today
    # is December 7th 2013
    @patch('workshops.models.datetime.date', FakeDate)
    def test_has_upcoming_events(self):
        """Test that the landing page is passed some
        upcoming_events in the context.
        """

        response = self.client.get(reverse('index'))

        # This will fail if the context variable doesn't exist
        upcoming_events = response.context['upcoming_events']

        # There are 2 upcoming events
        assert len(upcoming_events) == 2

        # They should all start with upcoming
        assert all([e.slug[:8] == 'upcoming' for e in upcoming_events])
