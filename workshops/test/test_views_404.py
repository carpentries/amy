from django.core.urlresolvers import reverse

from .base import TestBase


class TestViewsFor404ing(TestBase):
    """Make sure specific tests return 404 instead of 500."""

    def setUp(self):
        super()._setUpUsersAndLogin()

    def test_airport_details(self):
        url = reverse('airport_details', args=['ASD'])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_person_details(self):
        url = reverse('person_details', args=[404])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_person_edit(self):
        url = reverse('person_edit', args=[404])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_event_details(self):
        url = reverse('event_details', args=['non-existing-event'])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_validate_event(self):
        url = reverse('validate_event', args=['non-existing-event'])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_task_details(self):
        url = reverse('task_details', args=[404])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_badge_details(self):
        url = reverse('badge_details', args=['non-existing-badge'])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_eventrequest_assign(self):
        url = reverse('eventrequest_assign', args=[404, 404])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_revision_details(self):
        url = reverse('object_changes', args=[1234])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def todos_add(self):
        url = reverse('todos_add', args=['non-existing-event'])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)
