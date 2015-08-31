from django.core.urlresolvers import reverse

from ..models import Host, Event
from .base import TestBase


class TestHostNotes(TestBase):
    '''Test cases for Host notes.'''

    def test_fixture_notes(self):
        assert self.host_alpha.notes == '', \
            'Alpha Host notes should be empty'
        assert self.host_beta.notes == 'Notes\nabout\nBrazil\n', \
            'Beta Host notes incorrect'

    def test_host_created_without_notes(self):
        host = Host(domain='example.org',
                    fullname='Sample Example',
                    country='United-States')
        assert host.notes == '', \
            'Host created without notes should have empty notes'


class TestHost(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_host_delete(self):
        """Make sure deleted host is longer accessible.

        Additionally check on_delete behavior for Event."""
        Event.objects.create(host=self.host_alpha,
                             administrator=self.host_beta,
                             slug='test-event')

        for host_domain in [self.host_alpha.domain, self.host_beta.domain]:
            rv = self.client.get(reverse('host_delete', args=[host_domain, ]))
            content = rv.content.decode('utf-8')
            assert 'Failed to delete' in content

        Event.objects.get(slug='test-event').delete()

        for host_domain in [self.host_alpha.domain, self.host_beta.domain]:
            rv = self.client.get(reverse('host_delete', args=[host_domain, ]))
            assert rv.status_code == 302

            with self.assertRaises(Host.DoesNotExist):
                Host.objects.get(domain=host_domain)

    def test_host_invalid_chars_in_domain(self):
        """Ensure users can't put wrong characters in the host's domain field.

        Invalid characters are any that match `[^\w\.-]+`, ie. domain is
        allowed only to have alphabet-like chars, dot and dash.

        The reason for only these chars lies in `workshops/urls.py`.  The regex
        for the host_details URL has `[\w\.-]+` matching...
        """
        data = {
            'domain': 'http://beta.com/',
            'fullname': self.host_beta.fullname,
            'country': self.host_beta.country,
            'notes': self.host_beta.notes,
        }
        url = reverse('host_edit', args=[self.host_beta.domain])
        rv = self.client.post(url, data=data)
        # make sure we're not updating to good values
        assert rv.status_code == 200
