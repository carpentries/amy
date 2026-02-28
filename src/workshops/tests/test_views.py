from django.urls import reverse
from reversion.models import Revision
from reversion.revisions import create_revision

from src.workshops.models import Event, Role, Tag, Task
from src.workshops.tests.base import TestBase


class TestChangesLogView(TestBase):
    """Tests the view of recent changes."""

    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self.tag1, _ = Tag.objects.get_or_create(pk=1)

    def test_changes_log_links(self) -> None:
        """Regression test for https://github.com/carpentries/amy/issues/2456.

        This test isn't an effective regression test unless the PKs of the most recent
        revisions and versions are different, as the view used to use revision.pk
        when it should have used version.pk.
        """

        # Arrange
        # set up an event
        with create_revision():  # type: ignore[no-untyped-call]
            self.event = Event.objects.create(host=self.org_alpha, slug="event")
            self.event.tags.add(self.tag1)
            self.event.save()

        # Act
        # create a revision that generates two new versions,
        # to offset the pk counter between revisions and versions
        with create_revision():  # type: ignore[no-untyped-call]
            self.task = Task.objects.create(
                person=self.blackwidow,
                event=self.event,
                role=Role.objects.get(name="helper"),
            )

        # get the change we just made
        revision = Revision.objects.order_by("-date_created")[0]
        version = revision.version_set.all()[0]

        url = reverse("changes_log")
        rv = self.client.get(url)

        # Assert
        # check this is a valid test
        self.assertNotEqual(revision.pk, version.pk)
        self.assertEqual(rv.status_code, 200)

        # check that links point to the correct versions
        expected = f'<a href="/workshops/version/{version.pk}/">{version}</a>'
        self.assertContains(rv, expected, html=True)
