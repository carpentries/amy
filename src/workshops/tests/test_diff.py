from django.urls import reverse
from reversion import revisions as reversion
from reversion.models import Version
from reversion.revisions import create_revision

from src.workshops.models import Event, Person, Tag
from src.workshops.tests.base import TestBase


class TestRevisions(TestBase):
    def setUp(self) -> None:
        self._setUpUsersAndLogin()
        self._setUpOrganizations()
        self.tag1, _ = Tag.objects.get_or_create(pk=1)
        self.tag2, _ = Tag.objects.get_or_create(pk=2)

        with create_revision():  # type: ignore[no-untyped-call]
            self.event = Event.objects.create(host=self.org_alpha, slug="event")
            self.event.tags.add(self.tag1)
            self.event.save()

        with create_revision():  # type: ignore[no-untyped-call]
            self.event.slug = "better-event"
            self.event.host = self.org_beta
            self.event.tags.add(self.tag2)
            self.event.save()

        # load versions
        versions = Version.objects.get_for_object(self.event)
        assert len(versions) == 2
        self.newer, self.older = versions

    def test_showing_diff_event(self) -> None:
        # get newer revision page
        rv = self.client.get(reverse("object_changes", args=[self.newer.pk]))

        self.assertEqual(rv.status_code, 200)
        assert rv.context["version1"] == self.older
        assert rv.context["version2"] == self.newer
        assert rv.context["revision"] == self.newer.revision
        assert rv.context["object"] == self.event

    def test_diff_shows_coloured_labels(self) -> None:
        # get newer revision page
        rv = self.client.get(reverse("object_changes", args=[self.newer.pk]))
        # Red label for removed host
        self.assertContains(
            rv,
            f'<a class="label label-danger" href="{self.org_alpha.get_absolute_url()}">-{self.org_alpha}</a>',
            html=True,
        )
        # Green label for assigned host
        self.assertContains(
            rv,
            f'<a class="label label-success" href="{self.org_beta.get_absolute_url()}">+{self.org_beta}</a>',
            html=True,
        )
        # Grey label for pre-assigned tag
        self.assertContains(
            rv,
            f'<a class="label label-default" href="#">{self.tag1}</a>',
            html=True,
        )
        # Green label for additionally assigned tag
        self.assertContains(
            rv,
            f'<a class="label label-success" href="#">+{self.tag2}</a>',
            html=True,
        )

    def test_diff_shows_PK_for_deleted_relationships(self) -> None:
        # Delete the tag
        self.tag1.delete()
        self.tag2.delete()
        # get newer revision page
        rv = self.client.get(reverse("object_changes", args=[self.newer.pk]))
        self.assertContains(rv, '<a class="label label-default" href="#">1</a>', html=True)
        self.assertContains(rv, '<a class="label label-success" href="#">+2</a>', html=True)


class TestRegression1083(TestBase):
    def setUp(self) -> None:
        self._setUpUsersAndLogin()

    def test_regression_1083(self) -> None:
        with reversion.create_revision():  # type: ignore[no-untyped-call]
            alice = Person.objects.create_user(
                username="alice",
                personal="Alice",
                family="Jones",
                email="alice@jones.pl",
            )

        with reversion.create_revision():  # type: ignore[no-untyped-call]
            bob = Person.objects.create_user(username="bob", personal="Bob", family="Smith", email="bob@smith.pl")

        with reversion.create_revision():  # type: ignore[no-untyped-call]
            alice.family = "Williams"
            alice.save()
            bob.family = "Brown"
            bob.save()

        last_version = Version.objects.get_for_object(bob).select_related("revision", "revision__user")[0]
        revision = self.client.get(reverse("object_changes", args=[last_version.pk])).content.decode("utf-8")
        self.assertIn("Smith", revision)
        self.assertIn("Brown", revision)
