from django.urls import reverse
from reversion.models import Version
from reversion.revisions import create_revision
from reversion import revisions as reversion

from workshops.models import Event, Person, Tag
from workshops.tests.base import TestBase


class TestRevisions(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpOrganizations()
        self.tag1, _ = Tag.objects.get_or_create(pk=1)
        self.tag2, _ = Tag.objects.get_or_create(pk=2)

        with create_revision():
            self.event = Event.objects.create(host=self.org_alpha,
                                              slug='event')
            self.event.tags.add(self.tag1)
            self.event.save()

        with create_revision():
            self.event.slug = 'better-event'
            self.event.host = self.org_beta
            self.event.tags.add(self.tag2)
            self.event.save()

        # load versions
        versions = Version.objects.get_for_object(self.event)
        assert len(versions) == 2
        self.newer, self.older = versions

    def test_showing_diff_event(self):
        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[self.newer.pk]))

        self.assertEqual(rv.status_code, 200)
        assert rv.context['version1'] == self.older
        assert rv.context['version2'] == self.newer
        assert rv.context['revision'] == self.newer.revision
        assert rv.context['object'] == self.event

    def test_diff_shows_coloured_labels(self):
        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[self.newer.pk]))
        # Red label for removed host
        self.assertContains(rv,
            '<a class="label label-danger" href="{}">-{}</a>'.format(
                self.org_alpha.get_absolute_url(),
                self.org_alpha
            ),
            html=True
        )
        # Green label for assigned host
        self.assertContains(rv,
            '<a class="label label-success" href="{}">+{}</a>'.format(
                self.org_beta.get_absolute_url(),
                self.org_beta
            ),
            html=True
        )
        # Grey label for pre-assigned tag
        self.assertContains(rv,
            '<a class="label label-default" href="#">{}</a>'.format(
                self.tag1
            ),
            html=True
        )
        # Green label for additionally assigned tag
        self.assertContains(rv,
            '<a class="label label-success" href="#">+{}</a>'.format(
                self.tag2
            ),
            html=True
        )

    def test_diff_shows_PK_for_deleted_relationships(self):
        # Delete the tag
        self.tag1.delete()
        self.tag2.delete()
        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[self.newer.pk]))
        self.assertContains(rv,
            '<a class="label label-default" href="#">1</a>',
            html=True
        )
        self.assertContains(rv,
            '<a class="label label-success" href="#">+2</a>',
            html=True
        )


class TestRegression1083(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_regression_1083(self):
        with reversion.create_revision():
            alice = Person.objects.create_user(
                username='alice', personal='Alice', family='Jones',
                email='alice@jones.pl')

        with reversion.create_revision():
            bob = Person.objects.create_user(
                username='bob', personal='Bob', family='Smith',
                email='bob@smith.pl')

        with reversion.create_revision():
            alice.family = 'Williams'
            alice.save()
            bob.family = 'Brown'
            bob.save()

        res = self.app.get(reverse('person_details', args=[bob.pk]), user='admin')

        revision = res.click('Last modified on')
        self.assertIn('Smith', revision)
        self.assertIn('Brown', revision)

        back_to_person_view = revision.click('View newest')
        self.assertIn('Brown', back_to_person_view)
