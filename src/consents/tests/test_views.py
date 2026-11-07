from django.urls import reverse
from rest_framework import status

from src.consents.models import Consent, Term, TermOption, TermOptionChoices
from src.consents.tests.base import ConsentTestBase
from src.workshops.models import Person
from src.workshops.tests.base import consent_to_all_required_consents


class ConsentsUpdateTest(ConsentTestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpSuperuser()
        self._logSuperuserIn()
        self.person = Person.objects.create(personal="Harry", family="Potter", email="hp@magic.uk")

    def test_consents_update(self) -> None:
        """
        Ensures the ConsentsUpdate view is able to show
        and save all active terms.
        """
        preexisting_required_terms = Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE).active()

        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type=TermOptionChoices.AGREE,
            content="term1_option1",
        )
        TermOption.objects.create(
            term=term1,
            option_type=TermOptionChoices.AGREE,
            content="term1_option2",
        )
        term2 = Term.objects.create(content="term2", slug="term2")
        term2_option1 = TermOption.objects.create(
            term=term2,
            option_type=TermOptionChoices.AGREE,
        )
        term2_option2 = TermOption.objects.create(
            term=term2,
            option_type=TermOptionChoices.DECLINE,
        )
        original_term2_consent = self.reconsent(
            term=term2,
            term_option=term2_option2,
            person=self.person,
        )
        term3 = Term.objects.create(content="term3", slug="term3")
        TermOption.objects.create(
            term=term3,
            option_type=TermOptionChoices.AGREE,
        )
        term3_option2 = TermOption.objects.create(
            term=term3,
            option_type=TermOptionChoices.DECLINE,
        )
        original_term3_consent = self.reconsent(
            term=term3,
            term_option=term3_option2,
            person=self.person,
        )
        # Currently can only be called via redirect
        # from the PersonUpdate view. No direct consent edit view.
        person_edit_view = reverse("person_edit", kwargs={"person_id": self.person.pk})
        assert original_term3_consent.term_option  # for mypy
        data = {
            "consents-person": self.person.pk,
            f"consents-{term1.slug}": term1_option1.pk,
            f"consents-{term2.slug}": term2_option1.pk,
            f"consents-{term3.slug}": original_term3_consent.term_option.pk,
        }
        # Agree to required terms
        # Add required terms so that the test is not affected.
        # Adding the required terms because the form is bound
        # in the view and bound forms do not receive initial data.
        self.person_agree_to_terms(self.person, preexisting_required_terms)
        for consent in Consent.objects.filter(term__in=preexisting_required_terms).active():
            assert consent.term_option  # for mypy
            data[f"consents-{consent.term.slug}"] = consent.term_option.pk
        consents_path = reverse("consents_add", kwargs={"person_id": self.person.pk})
        result = self.client.post(f"{consents_path}?next={person_edit_view}", data)
        self.assertEqual(result.status_code, status.HTTP_302_FOUND)

        consents = Consent.objects.filter(person=self.person, term__in=[term1, term2, term3]).active()
        self.assertEqual(len(consents), 3)
        self.assertEqual(consents.filter(term=term1)[0].term_option, term1_option1)
        self.assertEqual(consents.filter(term=term2)[0].term_option, term2_option1)
        self.assertEqual(
            consents.filter(term=term3)[0].term_option,
            original_term3_consent.term_option,
        )

        # Old Consents are archived
        consents = Consent.objects.filter(
            person=self.person,
            term__in=[term1, term2, term3],
            archived_at__isnull=False,
        )
        self.assertEqual(len(consents), 4)
        self.assertCountEqual(
            [(c.term, c.term_option) for c in consents],
            [
                (term1, None),
                (term2, None),
                (term3, None),
                (term2, original_term2_consent.term_option),
            ],
        )


class ConsentsUpdateAccessTest(ConsentTestBase):
    """Regression tests for #3068: ConsentsUpdate was reachable without authentication."""

    def setUp(self) -> None:
        super().setUp()
        self.person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", username="potter_harry"
        )
        consent_to_all_required_consents(self.person)

        self.other = Person.objects.create(
            personal="Ron", family="Weasley", email="rw@magic.uk", username="weasley_ron"
        )
        consent_to_all_required_consents(self.other)

        self.term = Term.objects.create(content="Access test term", slug="access-test-term")
        self.agree = TermOption.objects.create(term=self.term, option_type=TermOptionChoices.AGREE)
        self.decline = TermOption.objects.create(term=self.term, option_type=TermOptionChoices.DECLINE)
        self.reconsent(term=self.term, term_option=self.agree, person=self.person)

    def url(self, person: Person, next_url: str | None = None) -> str:
        url = reverse("consents_add", kwargs={"person_id": person.pk})
        return f"{url}?next={next_url}" if next_url is not None else url

    def post_data(self, person: Person, option: TermOption) -> dict[str, int]:
        data = {"consents-person": person.pk, f"consents-{self.term.slug}": option.pk}
        for consent in Consent.objects.filter(person=person, term__required_type=Term.PROFILE_REQUIRE_TYPE).active():
            assert consent.term_option_id  # for mypy
            data[f"consents-{consent.term.slug}"] = consent.term_option_id
        return data

    def current_option(self, person: Person) -> TermOption | None:
        consent = Consent.objects.filter(person=person, term=self.term).active().first()
        return consent.term_option if consent else None

    def test_anonymous_post_redirects_to_login(self) -> None:
        url = self.url(self.person, next_url="/")
        result = self.client.post(url, self.post_data(self.person, self.decline))
        self.assertEqual(result.status_code, status.HTTP_302_FOUND)
        self.assertTrue(result["Location"].startswith(reverse("login")))
        self.assertEqual(self.current_option(self.person), self.agree)

    def test_anonymous_get_redirects_to_login(self) -> None:
        result = self.client.get(self.url(self.person, next_url="/"))
        self.assertEqual(result.status_code, status.HTTP_302_FOUND)
        self.assertTrue(result["Location"].startswith(reverse("login")))

    def test_get_not_allowed(self) -> None:
        self.client.force_login(self.person)
        result = self.client.get(self.url(self.person, next_url="/"))
        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_user_cannot_change_other_persons_consents(self) -> None:
        self.client.force_login(self.other)
        result = self.client.post(self.url(self.person, next_url="/"), self.post_data(self.person, self.decline))
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.current_option(self.person), self.agree)

    def test_posted_person_is_ignored(self) -> None:
        """Consents are saved for the person in the URL, not the one in the form data."""
        self.client.force_login(self.other)
        data = self.post_data(self.other, self.decline)
        data["consents-person"] = self.person.pk
        result = self.client.post(self.url(self.other, next_url="/"), data)
        self.assertEqual(result.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.current_option(self.person), self.agree)
        self.assertEqual(self.current_option(self.other), self.decline)

    def test_user_can_change_own_consents(self) -> None:
        self.client.force_login(self.person)
        result = self.client.post(self.url(self.person, next_url="/"), self.post_data(self.person, self.decline))
        self.assertRedirects(result, "/", fetch_redirect_response=False)
        self.assertEqual(self.current_option(self.person), self.decline)

    def test_unsafe_or_missing_next_falls_back_to_person_edit(self) -> None:
        self.client.force_login(self.person)
        person_edit = reverse("person_edit", kwargs={"person_id": self.person.pk})
        for next_url in ["https://evil.example.com/", None]:
            with self.subTest(next_url=next_url):
                result = self.client.post(
                    self.url(self.person, next_url=next_url), self.post_data(self.person, self.decline)
                )
                self.assertRedirects(result, person_edit, fetch_redirect_response=False)

    def test_invalid_form_redirects_back_with_error(self) -> None:
        self.client.force_login(self.person)
        data = self.post_data(self.person, self.decline)
        data[f"consents-{self.term.slug}"] = 999999  # not a valid option
        result = self.client.post(self.url(self.person, next_url="/"), data, follow=False)
        self.assertRedirects(result, "/", fetch_redirect_response=False)
        self.assertEqual(self.current_option(self.person), self.agree)
