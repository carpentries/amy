from django.core.urlresolvers import reverse

from ..models import Organization, Event
from .base import TestBase


class TestOrganizationNotes(TestBase):
    '''Test cases for Organization notes.'''

    def test_fixture_notes(self):
        assert self.org_alpha.notes == '', \
            'Alpha Organization notes should be empty'
        assert self.org_beta.notes == 'Notes\nabout\nBrazil\n', \
            'Beta Organization notes incorrect'

    def test_organization_created_without_notes(self):
        organization = Organization(domain='example.org',
                    fullname='Sample Example',
                    country='United-States')
        assert organization.notes == '', \
            'Organization created without notes should have empty notes'


class TestOrganization(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_organization_delete(self):
        """Make sure deleted organization is longer accessible.

        Additionally check on_delete behavior for Event."""
        Event.objects.create(host=self.org_alpha,
                             administrator=self.org_beta,
                             slug='test-event')

        for org_domain in [self.org_alpha.domain, self.org_beta.domain]:
            rv = self.client.post(reverse('organization_delete', args=[org_domain, ]))
            content = rv.content.decode('utf-8')
            assert 'Failed to delete' in content

        Event.objects.get(slug='test-event').delete()

        for org_domain in [self.org_alpha.domain, self.org_beta.domain]:
            rv = self.client.post(reverse('organization_delete', args=[org_domain, ]))
            assert rv.status_code == 302

            with self.assertRaises(Organization.DoesNotExist):
                Organization.objects.get(domain=org_domain)

    def test_organization_invalid_chars_in_domain(self):
        """Ensure users can't put wrong characters in the organization's domain field.

        Invalid characters are any that match `[^\w\.-]+`, ie. domain is
        allowed only to have alphabet-like chars, dot and dash.

        The reason for only these chars lies in `workshops/urls.py`.  The regex
        for the organization_details URL has `[\w\.-]+` matching...
        """
        data = {
            'domain': 'http://beta.com/',
            'fullname': self.org_beta.fullname,
            'country': self.org_beta.country,
            'notes': self.org_beta.notes,
        }
        url = reverse('organization_edit', args=[self.org_beta.domain])
        rv = self.client.post(url, data=data)
        # make sure we're not updating to good values
        assert rv.status_code == 200
