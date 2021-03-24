from typing import Iterable
from django.urls import reverse
from django.utils.http import urlencode

from workshops.tests.base import TestBase
from workshops.models import Person
from amy.consents.forms import RequiredConsentsForm
from consents.models import Consent, Term, TermOption


class TestActionRequiredTermView(TestBase):
    def setUp(self):
        super()._setUpAirports()
        super()._setUpBadges()
        self.create_required_consents()
        self.neville = Person.objects.create(
            personal="Neville",
            family="Longbottom",
            email="neville@longbottom.com",
            gender="M",
            username="longbottom_neville",
            airport=self.airport_0_0,
            is_active=True,
            # Setting old terms to True to ensure it doesn't affect anything.
            may_contact=True,
            publish_profile=True,
            data_privacy_agreement=True,
        )
        self.neville.save()

    def create_required_consents(self) -> None:
        user_privacy_policy = Term.objects.create(
            content="*I have read and agree to <a href="
            '"https://docs.carpentries.org/topic_folders/policies/privacy.html"'
            ' target="_blank" rel="noreferrer">'
            "the data privacy policy of The Carpentries</a>.",
            slug="privacy-policy",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        TermOption.objects.create(
            term=user_privacy_policy, option_type=TermOption.AGREE
        )
        may_contact = Term.objects.create(
            content="May contact: Allow to contact from The Carpentries according to"
            " the Privacy Policy.",
            slug="may-contact",
        )
        TermOption.objects.create(term=may_contact, option_type=TermOption.AGREE)
        TermOption.objects.create(term=may_contact, option_type=TermOption.DECLINE)
        optional_term = Term.objects.create(
            content="I'm an optional term",
            slug="optional-term",
        )
        TermOption.objects.create(term=optional_term, option_type=TermOption.AGREE)
        TermOption.objects.create(term=optional_term, option_type=TermOption.DECLINE)

    def person_agree_to_terms(self, person: Person, terms: Iterable[Term]) -> None:
        for term in terms:
            Consent.objects.create(
                person=person, term_option=term.options[0], term=term
            )

    def test_agreement_already_set(self):
        """Make sure the view redirect somewhere if person has already agreed
        to the privacy policy."""
        # force login Neville
        self.client.force_login(self.neville)

        url = reverse("action_required_terms")

        # form renders
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # Neville decided to agree to all terms on the page
        self.person_agree_to_terms(self.neville, RequiredConsentsForm.get_terms())

        # form throws 404
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_optional_agreements_are_optional(self):
        """Make sure the view redirect somewhere if person has agreed
        to the required terms."""
        # force login Neville
        self.client.force_login(self.neville)

        url = reverse("action_required_terms")

        # form renders
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # Neville decided to agree to only the required terms
        self.person_agree_to_terms(
            self.neville,
            Term.objects.filter(
                required_type=Term.PROFILE_REQUIRE_TYPE
            ).prefetch_active_options(),
        )

        # form throws 404
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_required_agreement_submit(self):
        "Make sure the form passes only when required terms are set."
        # setup sample data
        terms = RequiredConsentsForm.get_terms()
        data = {
            term.slug: term.options[0].pk
            for term in terms.exclude(required_type=Term.PROFILE_REQUIRE_TYPE)
        }
        data["person"] = self.neville.pk
        # make sure it doesn't pass without the required consents
        form = RequiredConsentsForm(data, person=self.neville)
        self.assertFalse(form.is_valid())

        # let's try with consent for privacy policy
        for term in terms.filter(required_type=Term.PROFILE_REQUIRE_TYPE):
            data[term.slug] = term.options[0].pk
        form = RequiredConsentsForm(data, person=self.neville)
        self.assertTrue(form.is_valid())


class TestActionRequiredPrivacyMiddleware(TestBase):
    def setUp(self):
        super()._setUpAirports()
        super()._setUpBadges()
        self.create_required_consents()
        self.neville = Person.objects.create(
            personal="Neville",
            family="Longbottom",
            email="neville@longbottom.com",
            gender="M",
            username="longbottom_neville",
            airport=self.airport_0_0,
            is_active=True,
            # Setting old terms to True to ensure it doesn't affect anything.
            may_contact=True,
            publish_profile=True,
            data_privacy_agreement=True,
        )
        self.neville.save()

    def test_anonymous_user(self):
        """Ensure anonymous user can reach anything."""
        urls = [
            reverse("login"),
            reverse("api:root"),
            reverse("training_request"),
            reverse("training_request_confirm"),
            reverse("workshop_request"),
            reverse("workshop_request_confirm"),
        ]
        # ensure we're not logged in
        self.client.logout()

        for url in urls:
            rv = self.client.get(url)
            # no redirects!
            self.assertEqual(rv.status_code, 200)
            # user indeed is anonymous
            self.assertEqual(rv.wsgi_request.user.is_anonymous, True)

    def test_logged_in_user(self):
        """Ensure logged-in user w/o privacy policy agreement is redirected
        to the form."""
        urls = [
            reverse("admin-dashboard"),
            reverse("trainee-dashboard"),
        ]

        form_url = reverse("action_required_privacy")

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(self.neville.data_privacy_agreement, False)

        for url in urls:
            rv = self.client.get(url)
            # redirects to the form
            self.assertEqual(rv.status_code, 302)
            self.assertTrue(rv["Location"].startswith(form_url))

    def test_no_more_redirects_after_agreement(self):
        """Ensure user is no longer forcefully redirected to accept the
        privacy policy."""
        url = reverse("trainee-dashboard")
        form_url = reverse("action_required_privacy")

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(self.neville.data_privacy_agreement, False)

        # we can't get to the url because we're redirected to the form
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 302)
        self.assertTrue(rv["Location"].startswith(form_url))

        # agree on the privacy policy
        self.neville.data_privacy_agreement = True
        self.neville.save()

        # now the dashboard is easily reachable
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

    def test_allowed_urls(self):
        form_url = reverse("action_required_privacy")
        urls = [
            reverse("logout"),
        ]
        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(self.neville.data_privacy_agreement, False)
        for url in urls:
            rv = self.client.get(url)
            # doesn't redirect to the form
            self.assertIn(rv.status_code, [200, 302])
            if "Location" in rv:
                self.assertNotEqual(rv["Location"], form_url)

    def test_next_param(self):
        """Ensure a non-dispatch URL is reachable through `?next` query
        string."""

        url = reverse("autoupdate_profile")
        form_url = reverse("action_required_privacy")
        form_url += "?{}".format(urlencode({"next": url}))

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(self.neville.data_privacy_agreement, False)

        # submit form
        rv = self.client.post(form_url, data=dict(data_privacy_agreement=True))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv["Location"], url)
