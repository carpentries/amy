from datetime import datetime, timedelta

from django.core.urlresolvers import reverse

from ..models import Event, Site
from .base import TestBase


class TestLandingPage(TestBase):
    "Tests for the workshop landing page"

    def setUp(self):
        self._setUpEvents()
        self._setUpUsersAndLogin()

    def test_has_upcoming_events(self):
        """Test that the landing page is passed some
        upcoming_events in the context.
        """

        response = self.client.get(reverse('dashboard'))

        # This will fail if the context variable doesn't exist
        upcoming_events = response.context['upcoming_events']

        # Count published upcoming events.
        assert len(upcoming_events) == self.num_upcoming

        # They should all be labeled 'upcoming'.
        assert all([('upcoming' in e.slug) for e in upcoming_events])
