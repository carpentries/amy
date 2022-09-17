from django.urls import reverse

from workshops.models import Event, Organization, Person
from workshops.tests.base import TestBase


class TestAssignments(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self.person = Person.objects.create_user(  # type: ignore
            username="test_user", email="user@test", personal="User", family="Test"
        )
        self.event = Event.objects.create(
            slug="event-for-assignment",
            host=Organization.objects.first(),
            assigned_to=None,
        )

    def test_assign_user_to_event(self):
        """Check if `event_assign` correctly assigns selected user
        to the event (use POST)."""
        assert self.event.assigned_to is None

        self.client.post(
            reverse("event_assign", args=[self.event.slug]),
            {"person": self.person.pk},
        )
        self.event.refresh_from_db()
        assert self.event.assigned_to == self.person

    def test_clear_assignment_from_event(self):
        """Check if `event_assign` correctly clears the assignment on selected
        event."""
        self.event.assigned_to = self.person
        self.event.save()

        assert self.event.assigned_to == self.person
        self.client.post(
            reverse("event_assign", args=[self.event.slug]),
            {"person": ""},
        )
        self.event.refresh_from_db()
        assert self.event.assigned_to is None
