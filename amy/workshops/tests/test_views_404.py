from django.urls import reverse

from workshops.tests.base import TestBase


class TestViewsFor404ing(TestBase):
    """Make sure specific views return 404 instead of 500."""

    def setUp(self) -> None:
        super()._setUpUsersAndLogin()

    def test_person_details(self) -> None:
        url = reverse("person_details", args=[404])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_person_edit(self) -> None:
        url = reverse("person_edit", args=[404])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_event_details(self) -> None:
        url = reverse("event_details", args=["non-existing-event"])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_validate_event(self) -> None:
        url = reverse("validate_event", args=["non-existing-event"])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_task_details(self) -> None:
        url = reverse("task_details", args=[404])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_badge_details(self) -> None:
        url = reverse("badge_details", args=["non-existing-badge"])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_revision_details(self) -> None:
        url = reverse("object_changes", args=[1234])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_organization_details(self) -> None:
        url = reverse("organization_details", args=["non-existing-org"])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)
