from django.contrib.auth.models import Group
from django.urls import reverse

from workshops.models import Event, Organization, Person, Tag
from workshops.tests.base import TestBase


class TestAdminDashboard(TestBase):
    """Tests for the admin dashboard."""

    def setUp(self):
        self._setUpEvents()
        self._setUpUsersAndLogin()

        # assign an upcoming event to the logged in user
        self.assigned_upcoming_event = Event.objects.active().upcoming_events().first()
        self.assigned_upcoming_event.assigned_to = self.admin
        self.assigned_upcoming_event.save()

        # assign an unpublished event to the logged in user
        self.assigned_unpublished_event = (
            Event.objects.active().unpublished_events().first()
        )
        self.assigned_unpublished_event.assigned_to = self.admin
        self.assigned_unpublished_event.save()

    def test_has_upcoming_events(self):
        """Test that the admin dashboard is passed some
        upcoming_events in the context."""

        # clear out assigned_to to avoid the default filtering
        response = self.client.get(f"{reverse('admin-dashboard')}?assigned_to=")

        # This will fail if the context variable doesn't exist
        events = response.context["current_events"]

        # all unassigned current events should be shown
        num_current_events = (
            Event.objects.current_events().filter(assigned_to=None).count()
        )
        self.assertEqual(len(events), num_current_events)

        # They should all be labeled 'upcoming'.
        assert all([("upcoming" in e.slug or "ongoing" in e.slug) for e in events])

    def test_no_inactive_events(self):
        """Make sure we don't display stalled or completed events on the
        dashboard."""
        stalled_tag = Tag.objects.get(name="stalled")
        unresponsive_tag = Tag.objects.get(name="unresponsive")
        cancelled_tag = Tag.objects.get(name="unresponsive")

        stalled = Event.objects.create(
            slug="stalled-event",
            host=Organization.objects.first(),
        )
        stalled.tags.add(stalled_tag)

        unresponsive = Event.objects.create(
            slug="unresponsive-event",
            host=Organization.objects.first(),
        )
        unresponsive.tags.add(unresponsive_tag)

        cancelled = Event.objects.create(
            slug="cancelled-event",
            host=Organization.objects.first(),
        )
        cancelled.tags.add(cancelled_tag)

        completed = Event.objects.create(
            slug="completed-event", completed=True, host=Organization.objects.first()
        )

        # stalled event appears in unfiltered list of events
        self.assertNotIn(stalled, Event.objects.unpublished_events())
        self.assertNotIn(unresponsive, Event.objects.unpublished_events())
        self.assertNotIn(cancelled, Event.objects.unpublished_events())
        self.assertNotIn(completed, Event.objects.unpublished_events())

        response = self.client.get(f"{reverse('admin-dashboard')}?assigned_to=")
        self.assertNotIn(stalled, response.context["unpublished_events"])
        self.assertNotIn(unresponsive, response.context["unpublished_events"])
        self.assertNotIn(cancelled, response.context["unpublished_events"])
        self.assertNotIn(completed, response.context["unpublished_events"])

    def test_events_default(self):
        """The admin dashboard shows the events assigned to the current logged in
        user by default (when the url is /dashboard/admin/)."""
        upcoming_event = Event.objects.upcoming_events().first()
        upcoming_event.assigned_to = self.admin
        upcoming_event.save()

        unpublished_event = Event.objects.active().unpublished_events().first()
        unpublished_event.assigned_to = self.admin
        unpublished_event.save()

        response = self.client.get(reverse("admin-dashboard"))

        # This will fail if the context variable doesn't exist
        current_events = response.context["current_events"]
        unpublished_events = response.context["unpublished_events"]
        assigned_to = response.context["assigned_to"]

        self.assertEqual(list(current_events), [upcoming_event])
        self.assertEqual(list(unpublished_events), [unpublished_event])
        self.assertEqual(assigned_to, self.admin)

    def test_events_assigned_to_none(self):
        """The admin dashboard shows all events if assigned to is None
        (when the url is /dashboard/admin/?assigned_to=)."""
        response = self.client.get(reverse("admin-dashboard"))

        # This will fail if the context variable doesn't exist
        current_events = response.context["current_events"]
        unpublished_events = response.context["unpublished_events"]
        assigned_to = response.context["assigned_to"]

        self.assertEqual(list(current_events), [self.assigned_upcoming_event])
        self.assertEqual(list(unpublished_events), [self.assigned_unpublished_event])
        self.assertEqual(assigned_to, self.admin)

    def test_events_assigned_to_another_user(self):
        """The admin dashboard shows all events assigned to a particular user
        if that user is specified in the assigned_to
        (when the url is /dashboard/admin/?assigned_to=other_user)."""
        other_admin = Person.objects.create_superuser(
            username="other_admin",
            personal="OtherSuper",
            family="User",
            email="other_sudo@example.org",
            password="admin",
        )
        other_admin.data_privacy_agreement = True  # TODO does this need to be here?
        other_admin.save()

        # Add an upcoming event to the logged in admin (self.admin)
        # and one to other_admin
        upcoming_event = (
            Event.objects.active()
            .filter(assigned_to__isnull=True)
            .upcoming_events()
            .first()
        )
        upcoming_event.assigned_to = other_admin
        upcoming_event.save()

        # Add an unpublished event to logged in admin (self.admin)
        # and another to other_admin
        unpublished_event = (
            Event.objects.active()
            .filter(assigned_to__isnull=True)
            .unpublished_events()
            .first()
        )
        unpublished_event.assigned_to = other_admin
        unpublished_event.save()

        response = self.client.get(
            f"{reverse('admin-dashboard')}?assigned_to={other_admin.id}"
        )

        # This will fail if the context variable doesn't exist
        current_events = response.context["current_events"]
        unpublished_events = response.context["unpublished_events"]
        assigned_to = response.context["assigned_to"]

        self.assertEqual(list(current_events), [upcoming_event])
        self.assertEqual(list(unpublished_events), [unpublished_event])
        self.assertEqual(assigned_to, other_admin)


class TestDispatch(TestBase):
    """Test that the right dashboard (trainee or admin dashboard) is displayed
    after logging in."""

    def test_superuser_logs_in(self):
        person = Person.objects.create_superuser(
            username="admin",
            personal="",
            family="",
            email="admin@example.org",
            password="pass",
        )
        person.data_privacy_agreement = True
        person.save()

        rv = self.client.post(
            reverse("login"), {"username": "admin", "password": "pass"}, follow=True
        )

        self.assertEqual(rv.resolver_match.view_name, "admin-dashboard")

    def test_mentor_logs_in(self):
        mentor = Person.objects.create_user(
            username="user",
            personal="",
            family="",
            email="mentor@example.org",
            password="pass",
        )
        admins = Group.objects.get(name="administrators")
        mentor.groups.add(admins)
        mentor.data_privacy_agreement = True
        mentor.save()

        rv = self.client.post(
            reverse("login"), {"username": "user", "password": "pass"}, follow=True
        )

        self.assertEqual(rv.resolver_match.view_name, "admin-dashboard")

    def test_steering_committee_member_logs_in(self):
        mentor = Person.objects.create_user(
            username="user",
            personal="",
            family="",
            email="user@example.org",
            password="pass",
        )
        steering_committee = Group.objects.get(name="steering committee")
        mentor.groups.add(steering_committee)
        mentor.data_privacy_agreement = True
        mentor.save()

        rv = self.client.post(
            reverse("login"), {"username": "user", "password": "pass"}, follow=True
        )

        self.assertEqual(rv.resolver_match.view_name, "admin-dashboard")

    def test_trainee_logs_in(self):
        self.trainee = Person.objects.create_user(
            username="trainee",
            personal="",
            family="",
            email="trainee@example.org",
            password="pass",
        )
        self.trainee.data_privacy_agreement = True
        self.trainee.save()

        rv = self.client.post(
            reverse("login"), {"username": "trainee", "password": "pass"}, follow=True
        )

        self.assertEqual(rv.resolver_match.view_name, "trainee-dashboard")
