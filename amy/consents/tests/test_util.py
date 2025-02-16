from django.test import TestCase
from django.utils import timezone

from consents.models import Consent, Term, TermEnum, TermOption, TermOptionChoices
from consents.tests.base import ConsentTestBase
from consents.util import (
    person_has_consented_to_required_terms,
    reconsent_for_term_option_type,
)
from workshops.models import Person


class TestActiveTermConsentsForm(ConsentTestBase):
    def test_person_has_consented_to_required_terms(self) -> None:
        # required term
        required_terms = Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE).active()
        self.assertNotEqual(len(required_terms), 0)
        # optional Term
        Term.objects.create(
            content="not_required_term",
            slug="not_required_term",
            required_type=Term.OPTIONAL_REQUIRE_TYPE,
        )
        # archived required term
        Term.objects.create(
            content="archived_term",
            slug="archived_term",
            archived_at=timezone.now(),
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        TermOption.objects.create(
            term=required_terms[0],
            option_type=TermOptionChoices.AGREE,
            archived_at=timezone.now(),
        )
        person = Person.objects.create(personal="Harry", family="Potter", email="hp@magic.uk")
        self.assertEqual(person_has_consented_to_required_terms(person), False)
        # Consents created for the required terms; should return True
        self.person_agree_to_terms(person, required_terms)
        self.assertEqual(person_has_consented_to_required_terms(person), True)


class TestReconsentForTermOptionType(TestCase):
    def test_term_not_found(self) -> None:
        # Arrange
        term_key = "test"  # this is incompatible with TermEnum and is ignored below
        term_option_type = TermOptionChoices.AGREE
        person = Person()

        # Act & Assert
        with self.assertRaises(Term.DoesNotExist):
            reconsent_for_term_option_type(
                term_key,  # type: ignore
                term_option_type,
                person,
            )

    def test_term_option_not_found(self) -> None:
        # Arrange
        term_key = TermEnum.MAY_CONTACT
        term_option_type = "test"  # incompatible with TermOptionChoices; ignored below
        person = Person()

        # Act & Assert
        with self.assertRaises(TermOption.DoesNotExist):
            reconsent_for_term_option_type(
                term_key,
                term_option_type,  # type: ignore
                person,
            )

    def test_consent_not_found(self) -> None:
        """Should not happen unless someone intentionally removes a Consent from DB."""
        # Arrange
        term_key = TermEnum.MAY_CONTACT
        term_option_type = TermOptionChoices.AGREE
        person = Person.objects.create(personal="Harry", family="Potter", email="hp@magic.uk")
        Consent.objects.filter(term__slug=Term.key_to_slug(term_key), person=person).delete()

        # Act & Assert
        with self.assertRaises(Consent.DoesNotExist):
            reconsent_for_term_option_type(
                term_key,
                term_option_type,
                person,
            )

    def test_old_consent_is_archived(self) -> None:
        # Arrange
        term_key = TermEnum.MAY_CONTACT
        term_option_type = TermOptionChoices.AGREE
        person = Person.objects.create(personal="Harry", family="Potter", email="hp@magic.uk")
        old_consent = Consent.objects.get(term__slug=Term.key_to_slug(term_key), person=person)

        # Act
        new_consent = reconsent_for_term_option_type(
            term_key,
            term_option_type,
            person,
        )
        old_consent.refresh_from_db()

        # Assert
        self.assertTrue(old_consent.is_archived())
        self.assertTrue(new_consent.is_active())

    def test_new_consent_created(self) -> None:
        # Arrange
        term_key = TermEnum.MAY_CONTACT
        term_option_type = TermOptionChoices.AGREE
        person = Person.objects.create(personal="Harry", family="Potter", email="hp@magic.uk")
        old_consent = Consent.objects.get(term__slug=Term.key_to_slug(term_key), person=person)

        # Act
        new_consent = reconsent_for_term_option_type(
            term_key,
            term_option_type,
            person,
        )

        # Assert
        self.assertNotEqual(old_consent.pk, new_consent.pk)
        self.assertEqual(old_consent.term, new_consent.term)
        self.assertIsNone(old_consent.term_option)
        # New consent term option is actually a value from database, whereas the old
        # consent was never set to anything but None (the default value).
        self.assertNotEqual(old_consent.term_option, new_consent.term_option)
        self.assertEqual(old_consent.person, new_consent.person)
