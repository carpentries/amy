from datetime import date, datetime, timedelta, timezone

from django.urls import reverse
from django_comments.models import Comment

from workshops.models import (
    Member,
    MemberRole,
    Membership,
    Organization,
    Person,
    TrainingRequest,
)
from workshops.tests.base import TestBase


class TestSearch(TestBase):
    """Test cases for searching."""

    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()

    def search_for(self, term: str, no_redirect: bool = True, follow: bool = False):  # type: ignore[no-untyped-def]
        return self.client.get(
            reverse("search"),
            data={"term": term, "no_redirect": "on" if no_redirect else ""},
            follow=follow,
        )

    def test_search_for_organization_with_no_matches(self) -> None:
        response = self.search_for("non.existent")
        self.assertEqual(response.status_code, 200)
        doc = response.content.decode("utf-8")
        self.assertNotIn("searchresult", doc, "Expected no search results")

    def test_search_for_organization_by_partial_name(self) -> None:
        response = self.search_for("Alpha")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # no way for us to check the url…
        self.assertIn(str(self.org_alpha.domain), content)

    def test_search_ignores_case(self) -> None:
        response = self.search_for("AlPhA")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # no way for us to check the url…
        self.assertIn(str(self.org_alpha.domain), content)

    def test_search_for_organization_by_full_domain(self) -> None:
        response = self.search_for("beta.com")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # no way for us to check the url…
        self.assertIn(str(self.org_beta.domain), content)

    def test_search_for_organization_with_multiple_matches(self) -> None:
        # 'a' is in both 'alpha' and 'beta'
        response = self.search_for("a")
        self.assertEqual(response.status_code, 200)
        doc = response.content.decode("utf-8")
        self.assertEqual(len(response.context["organisations"]), 3, "Expected three search results")
        for org in ["alpha.edu", "self-organized", "beta.com"]:
            self.assertIn(org, doc, "Wrong names {0} in search result".format(org))

    def test_search_for_people_by_personal_family_names(self) -> None:
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

    def test_search_for_people_by_secondary_email(self) -> None:
        """Test if searching by secondary email yields people correctly."""
        # Let's add Hermione Granger email as some organisation's name.
        # This is required because of redirection if only 1 person matches.
        org = Organization.objects.create(fullname="hermione2@granger.co.uk", domain="hgr.com")

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

    def test_search_for_training_requests(self) -> None:
        """Make sure that finding training requests works."""

        # added so that the search doesn't redirect with only 1 result
        Person.objects.create(
            personal="Victor",
            family="Krum",
            email="vkrum@durmstrang.edu",
            github="vkrum Lorem Ipsum Leprechauns",
        )

        TrainingRequest.objects.create(
            member_code="Leprechauns",
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

        response = self.search_for("Potter")
        self.assertEqual(len(response.context["training_requests"]), 0)

    def test_search_for_comments(self) -> None:
        """After switching from `notes` fields to comments, we need to make
        sure they're searchable."""
        Comment.objects.create(
            content_object=self.org_alpha,
            user=self.hermione,
            comment="Testing commenting system for Alpha Organization",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )

        response = self.search_for("Alpha")

        self.assertEqual(len(response.context["comments"]), 1)
        self.assertEqual(len(response.context["organisations"]), 1)

    def test_search_redirect(self) -> None:
        # search for "Alpha" (should yield 1 organisation)
        response = self.search_for("Alpha", no_redirect=False, follow=True)
        self.assertEqual(response.redirect_chain[0][0], self.org_alpha.get_absolute_url())

    def test_search_for_memberships_code(self) -> None:
        """Make sure that finding memberships by registration code works."""
        membership = Membership.objects.create(
            variant="partner",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.all()[0],
        )

        response = self.search_for("BETA-code")  # case-insensitive

        self.assertEqual(len(response.context["memberships"]), 1)
        self.assertEqual(len(response.context["organisations"]), 0)

    def test_search_for_memberships_name(self) -> None:
        """Make sure that finding memberships by name works."""
        membership = Membership.objects.create(
            name="alpha-name",
            variant="partner",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.all()[0],
        )

        response = self.search_for("ALPHA-name")  # case-insensitive

        self.assertEqual(len(response.context["memberships"]), 1)
        self.assertEqual(len(response.context["organisations"]), 0)

    def test_search_redirect_two_single_results(self) -> None:
        """Regression test: make sure redirect doesn't happen if two single results are
        present."""
        Comment.objects.create(
            content_object=self.org_alpha,
            user=self.hermione,
            comment="Testing commenting system for Alpha Organization",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )

        response = self.search_for("Alpha", no_redirect=False, follow=False)
        self.assertEqual(response.status_code, 200)  # doesn't redirect
        self.assertEqual(len(response.context["organisations"]), 1)
        self.assertEqual(len(response.context["comments"]), 1)

    def test_search_redirect_one_single_result(self) -> None:
        """Regression test: make sure redirect doesn't happen if there's a singular
        result in one of the groups, but other groups contain >= 2 elements.

        https://github.com/carpentries/amy/issues/2014
        """
        Comment.objects.create(
            content_object=self.org_alpha,
            user=self.hermione,
            comment="Testing commenting system for Alpha Organization",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )

        Comment.objects.create(
            content_object=self.org_beta,
            user=self.hermione,
            comment="Cross-posting an Alpha comment on Beta Organization page.",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )

        response = self.search_for("Alpha", no_redirect=False, follow=False)
        self.assertEqual(response.status_code, 200)  # doesn't redirect
        self.assertEqual(len(response.context["organisations"]), 1)
        self.assertEqual(len(response.context["comments"]), 2)
