from django.urls import reverse
from django_comments.models import Comment

from fiscal.forms import OrganizationCreateForm
from workshops.models import Organization, Event
from workshops.tests.base import TestBase


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
        r"""Ensure users can't put wrong characters in the organization's
        domain field.

        Invalid characters are any that match `[^\w\.-]+`, ie. domain is
        allowed only to have alphabet-like chars, dot and dash.

        The reason for only these chars lies in `workshops/urls.py`.  The regex
        for the organization_details URL has `[\w\.-]+` matching...
        """
        data = {
            'domain': 'http://beta.com/',
            'fullname': self.org_beta.fullname,
            'country': self.org_beta.country,
        }
        url = reverse('organization_edit', args=[self.org_beta.domain])
        rv = self.client.post(url, data=data)
        # make sure we're not updating to good values
        assert rv.status_code == 200

    def test_creating_event_with_no_comment(self):
        """Ensure that no comment is added when OrganizationCreateForm without
        comment content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            'fullname': 'Test Organization',
            'domain': 'test.org',
            'comment': '',
        }
        form = OrganizationCreateForm(data)
        form.save()
        self.assertEqual(Comment.objects.count(), 0)

    def test_creating_event_with_comment(self):
        """Ensure that a comment is added when OrganizationCreateForm with
        comment content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            'fullname': 'Test Organization',
            'domain': 'test.org',
            'comment': 'This is a test comment.',
        }
        form = OrganizationCreateForm(data)
        obj = form.save()
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.comment, 'This is a test comment.')
        self.assertIn(comment, Comment.objects.for_model(obj))
