from django.forms.widgets import HiddenInput
from django.urls import reverse
from django.utils.http import urlencode

from src.consents.forms import RequiredConsentsForm
from src.consents.models import Term
from src.consents.tests.base import ConsentTestBase
from src.consents.util import person_has_consented_to_required_terms
from src.workshops.models import Person


class TestActionRequiredTermView(ConsentTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.neville = Person.objects.create(
            personal="Neville",
            family="Longbottom",
            email="neville@longbottom.com",
            gender="M",
            username="longbottom_neville",
            airport_iata="CDG",
            is_active=True,
        )

    def test_agreement_already_set(self) -> None:
        """Make sure the view redirect somewhere if person has already agreed
        to the required terms."""
        # force login Neville
        self.client.force_login(self.neville)

        url = reverse("action_required_terms")

        # form renders
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # Neville decided to agree to all terms on the page
        kwargs = {
            "initial": {"person": self.neville},
            "widgets": {"person": HiddenInput()},
        }
        self.person_agree_to_terms(self.neville, RequiredConsentsForm(**kwargs).get_terms())

        # form throws 404
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_optional_agreements_are_optional(self) -> None:
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

    def test_required_agreement_submit(self) -> None:
        "Make sure the form passes only when required terms are set."
        # setup sample data
        kwargs = {
            "initial": {"person": self.neville},
            "widgets": {"person": HiddenInput()},
        }
        terms = RequiredConsentsForm(**kwargs).get_terms()
        data = {
            term.slug: term.options[0].pk  # type: ignore
            for term in terms.exclude(
                required_type=Term.PROFILE_REQUIRE_TYPE,
            )
        }
        data["person"] = self.neville.pk
        # make sure it doesn't pass without the required consents
        form = RequiredConsentsForm(data, initial={"person": self.neville})
        self.assertFalse(form.is_valid())

        # let's try with consent for required terms
        for term in terms.filter(required_type=Term.PROFILE_REQUIRE_TYPE):
            data[term.slug] = term.options[0].pk  # type: ignore
        form = RequiredConsentsForm(data, initial={"person": self.neville})
        self.assertTrue(form.is_valid())


class TestTermsMiddleware(ConsentTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.neville = Person.objects.create(
            personal="Neville",
            family="Longbottom",
            email="neville@longbottom.com",
            gender="M",
            username="longbottom_neville",
            airport_iata="CDG",
            is_active=True,
        )
        self.form_url = reverse("action_required_terms")

    def test_anonymous_user(self) -> None:
        """Ensure anonymous user is not redirected by the Terms middleware."""
        urls = [
            reverse("login"),
            reverse("api-v1:root"),
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

    def test_logged_in_user(self) -> None:
        """Ensure logged-in user who has not consented to
        the required terms is redirected to the form."""
        urls = [
            reverse("admin-dashboard"),
            reverse("instructor-dashboard"),
        ]

        # ensure we're logged in
        self.client.force_login(self.neville)
        # ensure we have not yet agreed to the required consents
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)
        with self.terms_middleware():
            for url in urls:
                rv = self.client.get(url)
                action_required_url = "{}?next={}".format(reverse("action_required_terms"), url)
                self.assertRedirects(rv, action_required_url)

    def test_no_more_redirects_after_agreement(self) -> None:
        """Ensure user is no longer forcefully redirected to accept the
        required terms."""
        url = reverse("instructor-dashboard")

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)

        with self.terms_middleware():
            # we can't get to the url because we're redirected to the form
            rv = self.client.get(url)
            action_required_url = "{}?next={}".format(reverse("action_required_terms"), url)
            self.assertRedirects(rv, action_required_url)

            # agree on the required terms
            self.person_agree_to_terms(
                self.neville,
                Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE),
            )

            # now the dashboard is easily reachable
            rv = self.client.get(url)
            self.assertEqual(rv.status_code, 200)

    def test_allowed_urls(self) -> None:
        url = reverse("logout")
        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)
        with self.terms_middleware():
            rv = self.client.post(url)
            # doesn't redirect to the form
            # But logout does redirect to login
            self.assertRedirects(rv, reverse("login"))

    def test_next_param(self) -> None:
        """Ensure a non-dispatch URL is reachable through `?next` query
        string."""

        url = reverse("autoupdate_profile")
        form_url = "{}?{}".format(reverse("action_required_terms"), urlencode({"next": url}))

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(person_has_consented_to_required_terms(self.neville), False)

        with self.terms_middleware():
            # fill in and submit form
            terms = Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE).prefetch_active_options()
            data = {"person": self.neville.pk}
            for term in terms:
                data[term.slug] = term.options[0].pk  # type: ignore
            rv = self.client.post(form_url, data=data)
            self.assertRedirects(rv, url)
