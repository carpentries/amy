from django.core.urlresolvers import reverse
from reversion import get_for_object, create_revision

from workshops.models import Event, Person

from .base import TestBase


class TestRevisions(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpHosts()

        with create_revision():
            self.event = Event.objects.create(host=self.host_alpha,
                                              slug='event')

        with create_revision():
            self.person = Person.objects.create(username='gh',
                                                personal='Hermione',
                                                family='Granger')

    def test_showing_diff_event(self):
        # change something
        with create_revision():
            self.event.slug = 'better-event'
            self.event.save()

        # load versions
        versions = get_for_object(self.event)
        assert len(versions) == 2
        newer, older = versions

        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[newer.revision.pk]))

        # test returned context
        context = rv.context
        assert context['previous_version'] == older
        assert context['current_version'] == newer
        assert context['revision'] == newer.revision
        assert context['object'] == self.event
        assert 'object_prev' in context
        assert context['object_prev'].__class__ == Event

    def test_showing_diff_person(self):
        # change something
        with create_revision():
            self.person.username = 'granger.hermione'
            self.person.save()

        # load versions
        versions = get_for_object(self.person)
        assert len(versions) == 2
        newer, older = versions

        # get newer revision page
        rv = self.client.get(reverse('object_changes',
                                     args=[newer.revision.pk]))

        # test returned context
        context = rv.context
        assert context['previous_version'] == older
        assert context['current_version'] == newer
        assert context['revision'] == newer.revision
        assert context['object'] == self.person
        assert 'object_prev' in context
        assert context['object_prev'].__class__ == Person
