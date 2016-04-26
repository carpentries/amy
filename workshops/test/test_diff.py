from django.core.urlresolvers import reverse
from reversion.revisions import get_for_object, create_revision

from workshops.models import Event, Person, Tag

from .base import TestBase


class TestRevisions(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpHosts()
        self.tag, _ = Tag.objects.get_or_create(pk=1)

        with create_revision():
            self.event = Event.objects.create(host=self.host_alpha,
                                              slug='event')

        with create_revision():
            self.event.slug = 'better-event'
            self.event.host = self.host_beta
            self.event.tags.add(self.tag)
            self.event.save()

        # load versions
        versions = get_for_object(self.event)
        assert len(versions) == 2
        self.newer, self.older = versions

    def test_showing_diff_event(self):
        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[self.newer.revision.pk]))
        # test returned context
        context = rv.context
        assert context['previous_version'] == self.older
        assert context['current_version'] == self.newer
        assert context['revision'] == self.newer.revision
        assert context['object'] == self.event
        assert 'object_prev' in context
        assert context['object_prev'].__class__ == Event


    def test_diff_shows_coloured_labels(self):
        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[self.newer.revision.pk]))
        # Red label for removed host
        self.assertContains(rv,
            '<a class="label label-danger" href="{}">-{}</a>'.format(
                self.host_alpha.get_absolute_url(),
                self.host_alpha
            ),
            html=True
        )
        # Green label for assigned host
        self.assertContains(rv,
            '<a class="label label-success" href="{}">+{}</a>'.format(
                self.host_beta.get_absolute_url(),
                self.host_beta
            ),
            html=True
        )
        # Green label for assigned tag
        self.assertContains(rv,
            '<a class="label label-success" href="#">+{}</a>'.format(
                self.tag
            ),
            html=True
        )

    def test_diff_shows_PK_for_deleted_relationships(self):
        # Delete the tag
        self.tag.delete()
        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[self.newer.revision.pk]))
        self.assertContains(rv,
            '<a class="label label-success" href="#">+1</a>',
            html=True
        )
