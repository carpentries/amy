from django.core.urlresolvers import reverse

from ..models import Site, Event
from .base import TestBase


class TestSiteNotes(TestBase):
    '''Test cases for Site notes.'''

    def test_fixture_notes(self):
        assert self.site_alpha.notes == '', \
            'Alpha Site notes should be empty'
        assert self.site_beta.notes == 'Notes\nabout\nBrazil\n', \
            'Beta Site notes incorrect'

    def test_site_created_without_notes(self):
        s = Site(domain='example.org',
                 fullname='Sample Example',
                 country='United-States')
        assert s.notes == '', \
            'Site created without notes should have empty notes'


class TestSite(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_site_delete(self):
        """Make sure deleted site is longer accessible.

        Additionally check on_delete behavior for Event."""
        Event.objects.create(site=self.site_alpha,
                             organizer=self.site_beta,
                             slug='test-event')

        for site_domain in [self.site_alpha.domain, self.site_beta.domain]:
            rv = self.client.get(reverse('site_delete', args=[site_domain, ]))
            content = rv.content.decode('utf-8')
            assert 'Failed to delete' in content

        Event.objects.get(slug='test-event').delete()

        for site_domain in [self.site_alpha.domain, self.site_beta.domain]:
            rv = self.client.get(reverse('site_delete', args=[site_domain, ]))
            assert rv.status_code == 302

            with self.assertRaises(Site.DoesNotExist):
                Site.objects.get(domain=site_domain)
