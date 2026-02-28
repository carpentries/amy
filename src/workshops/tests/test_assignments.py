from django.urls import reverse

from src.workshops.models import Event, Organization, Person
from src.workshops.tests.base import TestBase


class TestAssignments(TestBase):
    def setUp(self) -> None:
        self._setUpUsersAndLogin()
        self.person = Person.objects.create_user(
            username="test_user", email="user@test", personal="User", family="Test"
        )
        self.event = Event.objects.create(
            slug="event-for-assignment",
            host=Organization.objects.all()[0],
            assigned_to=None,
        )

    def test_assign_user_to_event(self) -> None:
        """Check if `event_assign` correctly assigns selected user
        to the event (use POST)."""
        assert self.event.assigned_to is None

        self.client.post(
            reverse("event_assign", args=[self.event.slug]),
            {"person": self.person.pk},
        )
        self.event.refresh_from_db()
        assert self.event.assigned_to == self.person

    def test_clear_assignment_from_event(self) -> None:
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
