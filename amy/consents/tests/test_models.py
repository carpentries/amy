from django.test import TestCase
from consents.models import Term, TermOption, Consent
from workshops.models import Person
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError


class TestQuerySet(TestCase):
    def test_term_active(self) -> None:
        Term.objects.create(content="term1", slug="term1", archived_at=timezone.now())
        term2 = Term.objects.create(
            content="term2",
            slug="term2",
        )
        term3 = Term.objects.create(
            content="term3",
            slug="term3",
        )

        self.assertCountEqual(Term.objects.active(), [term2, term3])

    def test_term_prefetch_active_options(self) -> None:
        term1 = Term.objects.create(
            content="term1", slug="term1", archived_at=timezone.now()
        )
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
        self.assertEqual(terms.filter(id=term1.id)[0].options, [term1_option1])
        self.assertEqual(terms.filter(id=term2.id)[0].options, [term2_option1])

    def test_consent_active(self) -> None:
        term1 = Term.objects.create(
            content="term1", slug="term1", archived_at=timezone.now()
        )
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
        Consent.objects.create(
            person=person1,
            term=term1,
            term_option=term1_option1,
            archived_at=timezone.now(),
        )
        consent1 = Consent.objects.create(
            person=person1, term=term1, term_option=term1_option1
        )
        consent2 = Consent.objects.create(
            person=person2, term=term1, term_option=term1_option1
        )
        consents = Consent.objects.active()

        self.assertCountEqual(consents, [consent1, consent2])


class TestConsentModel(TestCase):
    def test_unique_constraint(self) -> None:
        term1 = Term.objects.create(
            content="term1", slug="term1", archived_at=timezone.now()
        )
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
        Consent.objects.create(person=person1, term=term1, term_option=term1_option1)
        with self.assertRaises(IntegrityError):
            Consent.objects.create(
                person=person1, term=term1, term_option=term1_option2
            )

    def test_term_and_term_option_should_match(self):
        """Term was added to the Consent model to avoid too many complicated joins.
        The term option should always be related to the term stored in the table."""
        term1 = Term.objects.create(
            content="term1", slug="term1", archived_at=timezone.now()
        )
        term2_option1 = TermOption.objects.create(
            term=Term.objects.create(
                content="term2", slug="term2", archived_at=timezone.now()
            ),
            option_type="agree",
            content="option1",
        )
        person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        with self.assertRaisesRegex(
            ValidationError, r"Consent term\.id must match term_option\.term_id"
        ):
            Consent.objects.create(person=person, term=term1, term_option=term2_option1)
