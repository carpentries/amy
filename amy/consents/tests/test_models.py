from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from consents.exceptions import TermOptionDoesNotBelongToTermException
from consents.models import Consent, Term, TermOption
from consents.tests.base import ConsentTestBase
from workshops.models import Person


class TestQuerySet(ConsentTestBase):
    def test_term_active(self) -> None:
        term1 = Term.objects.create(
            content="term1", slug="term1", archived_at=timezone.now()
        )
        term2 = Term.objects.create(
            content="term2",
            slug="term2",
        )
        active_terms = Term.objects.active()
        self.assertNotIn(term1, active_terms)
        self.assertIn(term2, active_terms)

    def test_term_prefetch_active_options(self) -> None:
        term1 = Term.objects.create(content="term1", slug="term1")
        term2 = Term.objects.create(
            content="term2",
            slug="term2",
        )

        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option1",
        )
        TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option2",
            archived_at=timezone.now(),
        )
        term2_option1 = TermOption.objects.create(
            term=term2,
            option_type="agree",
            content="option1",
        )
        terms = Term.objects.all().prefetch_active_options()
        self.assertEqual(terms.filter(id=term1.id)[0].active_options, [term1_option1])
        self.assertEqual(terms.filter(id=term2.id)[0].active_options, [term2_option1])

    def test_consent_active(self) -> None:
        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option1",
        )
        person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        person2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="rweasley",
        )
        consent1 = self.reconsent(person1, term1, term1_option1)
        consent2 = self.reconsent(person2, term1, term1_option1)
        consents = Consent.objects.filter(
            term=term1, person__in=[person1, person2]
        ).active()

        self.assertCountEqual(consents, [consent1, consent2])


class TestConsentModel(ConsentTestBase):
    def test_is_archived_is_active_before_archiving(self) -> None:
        # Arrange
        term = Term.objects.create(content="term", slug="term")
        person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        consent = Consent.objects.get(person=person, term=term)

        # Act
        is_archived = consent.is_archived()
        is_active = consent.is_active()

        # Assert
        self.assertFalse(is_archived)
        self.assertTrue(is_active)

    def test_is_archived_is_active_after_archiving(self) -> None:
        # Arrange
        term = Term.objects.create(content="term", slug="term")
        person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        consent = Consent.objects.get(person=person, term=term)
        consent.archive()

        # Act
        is_archived = consent.is_archived()
        is_active = consent.is_active()

        # Assert
        self.assertTrue(is_archived)
        self.assertFalse(is_active)

    def test_unique_constraint(self) -> None:
        term1 = Term.objects.create(content="term1", slug="term1")
        TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option1",
        )
        term1_option2 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option2",
        )
        person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        # assert active consent exists for this term
        self.assertTrue(
            Consent.objects.filter(person=person1, term=term1).active().exists()
        )
        with self.assertRaises(IntegrityError):
            # create without archiving pre-existing active consent.
            Consent.objects.create(
                person=person1, term=term1, term_option=term1_option2
            )

    def test_term_and_term_option_should_match(self):
        """Term was added to the Consent model to avoid too many complicated joins.
        The term option should always be related to the term stored in the table."""
        # Arrange
        term1 = Term.objects.create(content="term1", slug="term1")
        term2 = Term.objects.create(content="term2", slug="term2")
        term2_option = TermOption.objects.create(
            term=term2,
            option_type="agree",
            content="option1",
        )
        person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )

        # Act & Assert
        with self.assertRaisesRegex(
            TermOptionDoesNotBelongToTermException,
            f"Consent self.term.pk={term1.pk} must match "
            f"self.term_option.term.pk={term2.pk}",
        ):
            Consent.objects.create(person=person, term=term1, term_option=term2_option)

    def test_term_options(self) -> None:
        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option1",
        )
        term1_option2 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option2",
        )
        term2 = Term.objects.create(content="term2", slug="term2")
        term2_option1 = TermOption.objects.create(
            term=term2,
            option_type="agree",
            content="option1",
        )
        term2_option2 = TermOption.objects.create(
            term=term2,
            option_type="agree",
            content="option2",
        )
        # Term options method is cached and requires only one
        # query even during subsequent calls
        with self.assertNumQueries(2):
            self.assertCountEqual(term1.options, [term1_option1, term1_option2])
            self.assertCountEqual(term2.options, [term2_option1, term2_option2])
            term1.options
            term2.options

        # term.options after prefetch_options does not need
        # an additional query
        terms = Term.objects.filter(
            slug__in=[term1.slug, term2.slug]
        ).prefetch_active_options()
        self.assertEqual(len(terms), 2)
        with self.assertNumQueries(0):
            self.assertCountEqual(terms[0].options, [term1_option1, term1_option2])
            self.assertCountEqual(terms[1].options, [term2_option1, term2_option2])
            self.assertCountEqual(term1.options, [term1_option1, term1_option2])
            self.assertCountEqual(term2.options, [term2_option1, term2_option2])

    def test_archive_all_for_person(self) -> None:
        """
        Archive all should archive the given consents
        then bulk create new unset consents.
        """
        terms = Term.objects.active()
        self.assertNotEqual(len(terms), 0)
        person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        person2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="rweasley",
        )
        # both people consent to all terms
        self.person_consent_active_terms(person1)
        self.person_consent_active_terms(person2)
        active_consents = Consent.objects.active()
        self.assertEqual(
            len(active_consents.filter(person=person1, term_option__isnull=False)),
            len(terms),
        )
        self.assertEqual(
            len(active_consents.filter(person=person2, term_option__isnull=False)),
            len(terms),
        )

        Consent.archive_all_for_person(person1)
        active_consents = Consent.objects.active()
        # All consents for person1 is archived. And a new unset consent is active
        self.assertEqual(
            len(active_consents.filter(person=person1, term_option__isnull=False)), 0
        )
        self.assertEqual(
            len(active_consents.filter(person=person1, term_option__isnull=True)),
            len(terms),
        )
        # person2 consents remain unchanged
        self.assertEqual(
            len(active_consents.filter(person=person2, term_option__isnull=False)),
            len(terms),
        )


class TestTermModel(ConsentTestBase):
    def test_archive(self):
        """
        Term archive method should archive the term
        and all related term options and consents.
        """
        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option1",
        )
        term1_option2 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option2",
        )

        person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        person2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="rweasley",
        )

        consent1 = self.reconsent(person1, term1, term1_option1)
        consent2 = self.reconsent(person2, term1, term1_option2)

        # Unrelated term, option, and consent.
        # They should not appear in the queries below
        unrelated_option = TermOption.objects.create(
            term=Term.objects.create(content="unrealted", slug="unrelated"),
            option_type="agree",
            content="option",
        )
        consent3 = self.reconsent(person2, unrelated_option.term, unrelated_option)

        term1.archive()

        # Term should be archived
        archived_term_ids = [
            term.pk for term in Term.objects.filter(archived_at__isnull=False)
        ]
        self.assertEqual(
            [term1.pk],
            archived_term_ids,
        )
        # Term options should be archived
        archived_term_option_ids = [
            option.pk for option in TermOption.objects.filter(archived_at__isnull=False)
        ]
        self.assertCountEqual(
            [term1_option1.pk, term1_option2.pk],
            archived_term_option_ids,
        )
        # Consents should be archived
        archived_consent_ids = [
            consent.pk for consent in Consent.objects.filter(archived_at__isnull=False)
        ]
        self.assertIn(consent1.pk, archived_consent_ids)
        self.assertIn(consent2.pk, archived_consent_ids)
        # Unrelated consent should not be archived
        self.assertNotIn(consent3.pk, archived_consent_ids)

    def test_clean(self):
        """Ensure required terms have at least one yes term option"""
        term = Term.objects.create(
            slug="required-test-term",
            content="term content",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        error_message = "Required term required-test-term must have agree term option."
        with self.assertRaisesMessage(ValidationError, error_message):
            term.clean()
        # Adding a no term is not enough
        TermOption.objects.create(
            term=term,
            option_type="decline",
            content="no",
        )
        with self.assertRaisesMessage(ValidationError, error_message):
            term.clean()
        # Adding a yes term is enough
        TermOption.objects.create(
            term=term,
            option_type="agree",
            content="yes",
        )
        # no error is thrown
        term.clean()


class TestTermOptionModel(ConsentTestBase):
    def test_archive(self):
        """
        TermOption archive method should archive the TermOption
        and all related consents.
        """
        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option1",
        )
        term1_option2 = TermOption.objects.create(
            term=term1,
            option_type="agree",
            content="option2",
        )

        person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        person2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="rweasley",
        )
        consent1 = self.reconsent(person1, term1, term1_option1)
        consent2 = self.reconsent(person2, term1, term1_option2)
        # Unrelated term, option, and consent.
        # They should not appear in the queries below
        unrelated_option = TermOption.objects.create(
            term=Term.objects.create(content="unrealted", slug="unrelated"),
            option_type="agree",
            content="option",
        )
        consent3 = self.reconsent(person2, unrelated_option.term, unrelated_option)

        term1_option1.archive()

        # Term should not be archived
        archived_term_ids = [
            term.pk for term in Term.objects.filter(archived_at__isnull=False)
        ]
        self.assertEqual(len(archived_term_ids), 0)

        # Only 1 Term options should be archived
        archived_term_option_ids = [
            option.pk for option in TermOption.objects.filter(archived_at__isnull=False)
        ]
        self.assertEqual(
            [term1_option1.pk],
            archived_term_option_ids,
        )

        # Only related consents should be archived
        archived_consent_ids = [
            consent.pk for consent in Consent.objects.filter(archived_at__isnull=False)
        ]
        self.assertIn(consent1.pk, archived_consent_ids)
        # Unrelated consent should not be archived
        self.assertNotIn(consent2.pk, archived_consent_ids)
        self.assertNotIn(consent3.pk, archived_consent_ids)

    def test_cannot_archive_only_yes_option_for_required_term(self) -> None:
        """Raise an error if trying to archive the only yes option in a required term"""
        term = Term.objects.create(
            slug="required-test-term",
            content="term content",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        term_option = TermOption.objects.create(
            term=term,
            option_type="agree",
            content="yes",
        )
        error_message = (
            "Term option {term_option} is the only agree term option for required term"
            " required-test-term."
            " Please add an additional agree option or archive the term instead."
        )
        with self.assertRaisesMessage(
            ValidationError, error_message.format(term_option=term_option)
        ):
            term_option.archive()
        # Adding another yes term
        new_yes_term = TermOption.objects.create(
            term=term,
            option_type="agree",
            content="new yes",
        )
        # We can now archive original yes term
        term_option.archive()
        # cannot archive new yes term
        with self.assertRaisesMessage(
            ValidationError, error_message.format(term_option=new_yes_term)
        ):
            new_yes_term.archive()
