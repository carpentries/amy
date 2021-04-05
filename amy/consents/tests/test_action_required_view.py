from amy.consents.tests.helpers import reconsent
from contextlib import contextmanager
from typing import Iterable

from consents.forms import RequiredConsentsForm
from consents.models import Term, TermOption
from consents.util import person_has_consented_to_required_terms
from django.urls import reverse
from django.utils.http import urlencode
from workshops.models import Person
from workshops.tests.base import TestBase


class ActionRequiredConsentTestBase(TestBase):
    @staticmethod
    def create_required_consents() -> None:
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
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        TermOption.objects.create(term=may_contact, option_type=TermOption.AGREE)
        TermOption.objects.create(term=may_contact, option_type=TermOption.DECLINE)
        optional_term = Term.objects.create(
            content="I'm an optional term",
            slug="optional-term",
        )
        TermOption.objects.create(term=optional_term, option_type=TermOption.AGREE)
        TermOption.objects.create(term=optional_term, option_type=TermOption.DECLINE)

    @staticmethod
    def person_agree_to_terms(person: Person, terms: Iterable[Term]) -> None:
        for term in terms:
            reconsent(person=person, term_option=term.options[0], term=term)

    @contextmanager
    def terms_middleware(self) -> None:
        """
        Remove workshops.action_required.PrivacyPolicy
        and replace it with consents.middleware.TermMiddleware
        """
        with self.modify_settings(
            MIDDLEWARE={
                "append": "consents.middleware.TermsMiddleware",
                "remove": ["workshops.action_required.PrivacyPolicy"],
            }
        ):
            yield


class TestActionRequiredTermView(ActionRequiredConsentTestBase):
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

    def test_agreement_already_set(self):
        """Make sure the view redirect somewhere if person has already agreed
        to the required terms."""
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
            Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE),
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
        form = RequiredConsentsForm(data, initial={"person": self.neville})
        self.assertFalse(form.is_valid())

        # let's try with consent for required terms
        for term in terms.filter(required_type=Term.PROFILE_REQUIRE_TYPE):
            data[term.slug] = term.options[0].pk
        form = RequiredConsentsForm(data, initial={"person": self.neville})
        self.assertTrue(form.is_valid())


class TestTermsMiddleware(ActionRequiredConsentTestBase):
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
        self.form_url = reverse("action_required_terms")

    def test_anonymous_user(self):
        """Ensure anonymous user is not redirected by the Terms middleware."""
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
        """Ensure logged-in user who has not consented to
        the required terms is redirected to the form."""
        urls = [
            reverse("admin-dashboard"),
            reverse("trainee-dashboard"),
        ]

        # ensure we're logged in
        self.client.force_login(self.neville)
        # ensure we have not yet agreed to the required consents
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)
        with self.terms_middleware():
            for url in urls:
                rv = self.client.get(url)
                action_required_url = "{}?next={}".format(
                    reverse("action_required_terms"), url
                )
                self.assertRedirects(rv, action_required_url)

    def test_no_more_redirects_after_agreement(self):
        """Ensure user is no longer forcefully redirected to accept the
        required terms."""
        url = reverse("trainee-dashboard")

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)

        with self.terms_middleware():
            # we can't get to the url because we're redirected to the form
            rv = self.client.get(url)
            action_required_url = "{}?next={}".format(
                reverse("action_required_terms"), url
            )
            self.assertRedirects(rv, action_required_url)

            # agree on the required terms
            self.person_agree_to_terms(
                self.neville,
                Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE),
            )

            # now the dashboard is easily reachable
            rv = self.client.get(url)
            self.assertEqual(rv.status_code, 200)

    def test_allowed_urls(self):
        url = reverse("logout")
        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)
        with self.terms_middleware():
            rv = self.client.get(url)
            # doesn't redirect to the form
            # But logout does redirect to login
            self.assertRedirects(rv, reverse("login"))

    def test_next_param(self):
        """Ensure a non-dispatch URL is reachable through `?next` query
        string."""

        url = reverse("autoupdate_profile")
        form_url = "{}?{}".format(
            reverse("action_required_terms"), urlencode({"next": url})
        )

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)

        with self.terms_middleware():
            # fill in and submit form
            terms = Term.objects.filter(
                required_type=Term.PROFILE_REQUIRE_TYPE
            ).prefetch_active_options()
            data = {"person": self.neville.pk}
            for term in terms:
                data[term.slug] = term.options[0].pk
            rv = self.client.post(form_url, data=data)
            self.assertRedirects(rv, url)

    def test_old_terms_do_not_affect_terms_middleware(self):
        """
        User is redirected even if old terms are false.
        """
        urls = [
            reverse("admin-dashboard"),
            reverse("trainee-dashboard"),
        ]
        harry = Person.objects.create(
            personal="Harry",
            family="Potter",
            email="harry@howarts.com",
            gender="M",
            username="harry_potter",
            airport=self.airport_0_0,
            is_active=True,
            # Setting old terms to False.
            may_contact=False,
            publish_profile=False,
            data_privacy_agreement=False,
        )

        # ensure we're logged in
        self.client.force_login(harry)
        # ensure we have not yet agreed to the required consents
        self.assertEqual(person_has_consented_to_required_terms(harry), False)
        with self.terms_middleware():
            for url in urls:
                rv = self.client.get(url)
                # redirects to the form
                action_required_url = "{}?next={}".format(
                    reverse("action_required_terms"), url
                )
                self.assertRedirects(rv, action_required_url)
