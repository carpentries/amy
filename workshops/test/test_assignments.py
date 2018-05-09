from django.urls import reverse

from ..models import Person, Event, EventRequest
from .base import TestBase


class TestAssignments(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpEvents()

    def test_assign_user_to_event(self):
        """Check if `event_assign` correctly assigns selected user
        to the event."""
        event = Event.objects.first()
        user = Person.objects.first()

        assert event.assigned_to is None

        self.client.get(reverse('event_assign',
                                args=[event.slug, user.pk]))
        event.refresh_from_db()
        assert event.assigned_to == user

    def test_assign_user_to_eventrequest(self):
        """Check if `eventrequest_assign` correctly assigns selected user
        to the workshop request."""
        er = EventRequest.objects.create(
            name='Harry Potter', email='harry@potter.com',
            affiliation='Hogwarts', location='United Kingdom',
            country='GB', workshop_type='swc',
        )
        user = Person.objects.first()

        assert er.assigned_to is None

        self.client.get(reverse('eventrequest_assign',
                                args=[er.pk, user.pk]))
        er.refresh_from_db()
        assert er.assigned_to == user

    def test_assign_user_to_event_POST(self):
        """Check if `event_assign` correctly assigns selected user
        to the event (use POST)."""
        event = Event.objects.first()
        user = Person.objects.first()

        assert event.assigned_to is None

        fake_user_pk = 0

        self.client.post(
            reverse('event_assign', args=[event.slug, fake_user_pk]),
            {'person_1': user.pk},
        )
        event.refresh_from_db()
        assert event.assigned_to == user

    def test_assign_user_to_eventrequest_POST(self):
        """Check if `eventrequest_assign` correctly assigns selected user
        to the workshop request (use POST)."""
        er = EventRequest.objects.create(
            name='Harry Potter', email='harry@potter.com',
            affiliation='Hogwarts', location='United Kingdom',
            country='GB', workshop_type='swc',
        )
        user = Person.objects.first()

        assert er.assigned_to is None

        fake_user_pk = 0

        self.client.post(
            reverse('eventrequest_assign', args=[er.pk, fake_user_pk]),
            {'person_1': user.pk},
        )
        er.refresh_from_db()
        assert er.assigned_to == user

    def test_clear_assignment_from_event(self):
        """Check if `event_assign` correctly clears the assignment on selected
        event."""
        event = Event.objects.first()
        user = Person.objects.first()
        event.assigned_to = user
        event.save()

        assert event.assigned_to == user
        self.client.get(reverse('event_assign', args=[event.slug]))
        event.refresh_from_db()
        assert event.assigned_to is None

    def test_clear_assignment_from_eventrequest(self):
        """Check if `eventrequest_assign` correctly clears the assignment on
        selected workshop request."""
        user = Person.objects.first()
        # add a minimal request
        er = EventRequest.objects.create(
            name='Harry Potter', email='harry@potter.com',
            affiliation='Hogwarts', location='United Kingdom',
            country='GB', workshop_type='swc',
            assigned_to=user,
        )

        assert er.assigned_to == user
        self.client.get(reverse('eventrequest_assign', args=[er.pk]))
        er.refresh_from_db()
        assert er.assigned_to is None
