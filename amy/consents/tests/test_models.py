from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from consents.tests.base import ConsentTestBase
from consents.models import Consent, Term, TermOption
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
        term1 = Term.objects.create(content="term1", slug="term1")
        term2_option1 = TermOption.objects.create(
            term=Term.objects.create(content="term2", slug="term2"),
            option_type="agree",
            content="option1",
        )
        person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        with self.assertRaisesRegex(
            ValidationError, "Consent term.id must match term_option.term_id"
        ):
            Consent.objects.create(person=person, term=term1, term_option=term2_option1)

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
