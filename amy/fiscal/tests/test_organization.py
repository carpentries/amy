from django.urls import reverse
from django_comments.models import Comment

from fiscal.forms import OrganizationCreateForm, OrganizationForm
from workshops.models import Event, Organization
from workshops.tests.base import TestBase


class TestOrganization(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_organization_delete(self):
        """Make sure deleted organization is longer accessible.

        Additionally check on_delete behavior for Event."""
        Event.objects.create(
            host=self.org_alpha, administrator=self.org_beta, slug="test-event"
        )

        for org_domain in [self.org_alpha.domain_quoted, self.org_beta.domain_quoted]:
            rv = self.client.post(
                reverse(
                    "organization_delete",
                    args=[
                        org_domain,
                    ],
                )
            )
            content = rv.content.decode("utf-8")
            assert "Failed to delete" in content

        Event.objects.get(slug="test-event").delete()

        for org_domain in [self.org_alpha.domain_quoted, self.org_beta.domain_quoted]:
            rv = self.client.post(
                reverse(
                    "organization_delete",
                    args=[
                        org_domain,
                    ],
                )
            )
            assert rv.status_code == 302

            with self.assertRaises(Organization.DoesNotExist):
                Organization.objects.get(domain=org_domain)

    def test_organization_invalid_chars_in_domain(self):
        """Ensure organisation's domain is cleaned from URL scheme, if it was present.
        Ensure other parts of the URL remain.

        The cleaning exists in OrganizationForm.clean_domain.
        """
        test_data = [
            ("http://example.com/", "example.com/"),
            ("https://example.com/", "example.com/"),
            ("ftp://example.com/", "example.com/"),
            ("http://example.com", "example.com"),
            ("//example.com", "example.com"),
            ("//example.com/", "example.com/"),
            ("//example.com/?query", "example.com/?query"),
            ("//example.com/path/", "example.com/path/"),
            ("//example.com/path", "example.com/path"),
            ("//example.com:80/path/?query", "example.com:80/path/?query"),
            ("example.com/path;params?query#fragment", "example.com/path?query"),
            (
                "//user:password@example.com:80/path?query",
                "user:password@example.com:80/path?query",
            ),
        ]
        for domain, expected in test_data:
            with self.subTest(domain=domain):
                form = OrganizationForm({"domain": domain})
                form.full_clean()
                self.assertIn("domain", form.cleaned_data)
                self.assertEqual(form.cleaned_data["domain"], expected)

    def test_creating_organization_with_no_comment(self):
        """Ensure that no comment is added when OrganizationCreateForm without
        comment content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "fullname": "Test Organization",
            "domain": "test.org",
            "comment": "",
        }
        form = OrganizationCreateForm(data)
        form.save()
        self.assertEqual(Comment.objects.count(), 0)

    def test_creating_organization_with_comment(self):
        """Ensure that a comment is added when OrganizationCreateForm with
        comment content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "fullname": "Test Organization",
            "domain": "test.org",
            "comment": "This is a test comment.",
        }
        form = OrganizationCreateForm(data)
        obj = form.save()
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.comment, "This is a test comment.")
        self.assertIn(comment, Comment.objects.for_model(obj))

    def test_symmetrical_affiliations(self):
        """Make sure adding an affiliation in one organisation, automatically reveals
        this relationship in the other organisation."""
        # Arrange - `setUp()` creates 2 organisations we can use

        # Act
        self.org_alpha.affiliated_organizations.add(self.org_beta)

        # Assert
        self.assertIn(self.org_beta, self.org_alpha.affiliated_organizations.all())
        self.assertIn(self.org_alpha, self.org_beta.affiliated_organizations.all())

    def test_manager_administrators(self):
        """Ensure the correct organizations are returned as possible administrators."""
        # Arrange - `setUp()` also creates 2 organisations these filters should ignore
        self._setUpAdministrators()
        expected_domains = [
            "self-organized",
            "software-carpentry.org",
            "datacarpentry.org",
            "librarycarpentry.org",
            # Instructor Training organisation
            "carpentries.org",
            # Collaborative Lesson Development Training organisation
            "carpentries.org/community-lessons/",
        ]

        # Act
        organizations_with_admin_domain = Organization.objects.filter(
            domain__in=expected_domains
        )
        administrators = Organization.objects.administrators()

        # Assert
        # check that all ADMIN_DOMAINS are represented
        self.assertSetEqual(
            set(expected_domains), set(Organization.objects.ADMIN_DOMAINS)
        )
        self.assertEqual(organizations_with_admin_domain.count(), len(expected_domains))
        # check that administrators() returns what we expect
        self.assertQuerySetEqual(organizations_with_admin_domain, administrators)
