from datetime import datetime, timezone

from django.contrib.sites.models import Site
from django.urls import reverse
from django_comments.models import Comment

from workshops.tests.base import TestBase
from workshops.models import Organization, Person, TrainingRequest


class TestSearch(TestBase):
    """Test cases for searching."""

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def search_for(self, term, no_redirect=True, follow=False):
        search_page = self.app.get(reverse("search"), user="admin")
        form = search_page.forms["main-form"]
        form["term"] = term
        form["no_redirect"] = no_redirect
        if follow:
            return form.submit().maybe_follow()
        return form.submit()

    def test_search_for_organization_with_no_matches(self):
        response = self.search_for("non.existent")
        self.assertEqual(response.status_code, 200)
        doc = response.content.decode("utf-8")
        self.assertNotIn("searchresult", doc, "Expected no search results")

    def test_search_for_organization_by_partial_name(self):
        response = self.search_for("Alpha")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # no way for us to check the url…
        self.assertIn(str(self.org_alpha.domain), content)

    def test_search_ignores_case(self):
        response = self.search_for("AlPhA")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # no way for us to check the url…
        self.assertIn(str(self.org_alpha.domain), content)

    def test_search_for_organization_by_full_domain(self):
        response = self.search_for("beta.com")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # no way for us to check the url…
        self.assertIn(str(self.org_beta.domain), content)

    def test_search_for_organization_with_multiple_matches(self):
        # 'a' is in both 'alpha' and 'beta'
        response = self.search_for("a")
        self.assertEqual(response.status_code, 200)
        doc = response.content.decode("utf-8")
        self.assertEqual(
            len(response.context["organisations"]), 3, "Expected three search results"
        )
        for org in ["alpha.edu", "self-organized", "beta.com"]:
            self.assertIn(org, doc, "Wrong names {0} in search result".format(org))

    def test_search_for_people_by_personal_family_names(self):
        """Test if searching for two words yields people correctly."""
        # let's add Hermione Granger to some organization's notes
        # this is required because of redirection if only 1 person matches
        org = Organization.objects.create(fullname="Hermione Granger", domain="hgr.com")

        response = self.search_for("Hermione Granger")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["persons"]) + len(response.context["organisations"]),
            2,
            "Expected two search results",
        )
        self.assertIn(org, response.context["organisations"])
        self.assertIn(self.hermione, response.context["persons"])

    def test_search_for_people_by_secondary_email(self):
        """Test if searching by secondary email yields people correctly."""
        # Let's add Hermione Granger email as some organisation's name.
        # This is required because of redirection if only 1 person matches.
        org = Organization.objects.create(
            fullname="hermione2@granger.co.uk", domain="hgr.com"
        )

        # make sure Hermione has individual secondary email
        self.hermione.secondary_email = "hermione2@granger.co.uk"
        self.hermione.save()

        response = self.search_for("hermione2@granger.co.uk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["persons"]) + len(response.context["organisations"]),
            2,
            "Expected two search results",
        )
        self.assertIn(org, response.context["organisations"])
        self.assertIn(self.hermione, response.context["persons"])

    def test_search_for_training_requests(self):
        """Make sure that finding training requests works."""

        # added so that the search doesn't redirect with only 1 result
        Person.objects.create(
            personal="Victor",
            family="Krum",
            email="vkrum@durmstrang.edu",
            github="vkrum Lorem Ipsum Leprechauns",
        )

        TrainingRequest.objects.create(
            group_name="Leprechauns",
            personal="Victor",
            family="Krum",
            email="vkrum@durmstrang.edu",
            github="vkrum",
            user_notes="Lorem Ipsum",
        )

        response = self.search_for("Leprechaun")
        self.assertEqual(len(response.context["training_requests"]), 1)

        response = self.search_for("Krum")
        self.assertEqual(len(response.context["training_requests"]), 1)

        response = self.search_for("Lorem")
        self.assertEqual(len(response.context["training_requests"]), 1)

        # do not search in_persons, otherwise it'd redirect to Harry Potter's
        # profile
        response = self.search_for("Potter")
        self.assertEqual(len(response.context["training_requests"]), 0)

    def test_search_for_comments(self):
        """After switching from `notes` fields to comments, we need to make
        sure they're searchable."""
        Comment.objects.create(
            content_object=self.org_alpha,
            user=self.hermione,
            comment="Testing commenting system for Alpha Organization",
            submit_date=datetime.now(tz=timezone.utc),
            site=Site.objects.get_current(),
        )

        # search for "Alpha" in organisations and comments
        response = self.search_for("Alpha")

        self.assertEqual(len(response.context["comments"]), 1)
        self.assertEqual(len(response.context["organisations"]), 1)

        # search for "Alpha" only in comments + check redirect
        response = self.search_for("Alpha", no_redirect=False, follow=True)
        self.assertEqual(response.request.path, self.org_alpha.get_absolute_url())
