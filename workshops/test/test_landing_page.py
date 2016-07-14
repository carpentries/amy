from django.contrib.auth.models import Group

from django.core.urlresolvers import reverse

from ..models import Event, Organization, Tag, Person
from .base import TestBase


class TestAdminDashboard(TestBase):
    """ Tests for the admin dashboard. """

    def setUp(self):
        self._setUpEvents()
        self._setUpUsersAndLogin()

    def test_has_upcoming_events(self):
        """Test that the admin dashboard is passed some
        upcoming_events in the context.
        """

        response = self.client.get(reverse('admin-dashboard'))

        # This will fail if the context variable doesn't exist
        events = response.context['current_events']

        # They should all be labeled 'upcoming'.
        assert all([('upcoming' in e.slug or 'ongoing' in e.slug)
                    for e in events])

    def test_no_inactive_events(self):
        """Make sure we don't display stalled or completed events on the
        dashboard."""
        stalled_tag = Tag.objects.get(name='stalled')
        stalled = Event.objects.create(
            slug='stalled-event', host=Organization.objects.first(),
        )
        stalled.tags.add(stalled_tag)
        completed = Event.objects.create(slug='completed-event',
                                         completed=True,
                                         host=Organization.objects.first())

        # stalled event appears in unfiltered list of events
        self.assertIn(stalled, Event.objects.unpublished_events())
        self.assertIn(completed, Event.objects.unpublished_events())

        response = self.client.get(reverse('admin-dashboard'))
        self.assertNotIn(stalled, response.context['unpublished_events'])
        self.assertNotIn(completed, response.context['unpublished_events'])


class TestTraineeDashboard(TestBase):
    """ Tests for trainee dashboard. """
    def setUp(self):
        self.user = Person.objects.create_user(
            username='user', personal='', family='',
            email='user@example.org', password='pass')
        self.client.login(username='user', password='pass')

    def test_dashboard_loads(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self.assertIn("Log out", content)
        self.assertIn("Update your profile", content)


class TestDispatch(TestBase):
    """ Test that the right dashboard (trainee or admin dashboard) is displayed
    after logging in."""

    def test_superuser_logs_in(self):
        Person.objects.create_superuser(
            username='admin', personal='', family='',
            email='admin@example.org', password='pass')

        rv = self.client.post(reverse('login'),
                              {'username':'admin', 'password':'pass'},
                              follow=True)

        self.assertEqual(rv.resolver_match.view_name, 'admin-dashboard')

    def test_mentor_logs_in(self):
        mentor = Person.objects.create_user(
            username='user', personal='', family='',
            email='mentor@example.org', password='pass')
        admins = Group.objects.get(name='administrators')
        mentor.groups.add(admins)

        rv = self.client.post(reverse('login'),
                              {'username': 'user', 'password': 'pass'},
                              follow=True)

        self.assertEqual(rv.resolver_match.view_name, 'admin-dashboard')

    def test_trainee_logs_in(self):
        self.trainee = Person.objects.create_user(
            username='trainee', personal='', family='',
            email='trainee@example.org', password='pass')

        rv = self.client.post(reverse('login'),
                              {'username': 'trainee', 'password': 'pass'},
                              follow=True)

        self.assertEqual(rv.resolver_match.view_name, 'trainee-dashboard')
