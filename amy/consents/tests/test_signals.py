from django.utils import timezone

from consents.models import Consent, Person, Term
from consents.tests.base import ConsentTestBase


class TestTermModel(ConsentTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        self.person2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="rw",
        )

    def test_unset_consents_are_created_on_term_create(self) -> None:
        term1 = Term.objects.create(
            content="term1",
            slug="term1",
        )
        consents = Consent.objects.filter(term=term1)
        self.assertEqual(len(consents), 2)

        consent1 = consents.filter(person=self.person1)[0]
        self.assertIsNone(consent1.term_option)
        self.assertIsNone(consent1.archived_at)

        consent2 = consents.filter(person=self.person2)[0]
        self.assertIsNone(consent2.term_option)
        self.assertIsNone(consent2.archived_at)

        # Update the term; new consents should not change
        term1.content = "New content"
        term1.save()
        consents = Consent.objects.filter(term=term1)
        self.assertEqual(len(consents), 2)

        consent1 = consents.filter(person=self.person1)[0]
        self.assertIsNone(consent1.term_option)
        self.assertIsNone(consent1.archived_at)

        consent2 = consents.filter(person=self.person2)[0]
        self.assertIsNone(consent2.term_option)
        self.assertIsNone(consent2.archived_at)

    def test_unset_consents_are_created_on_person_create(self) -> None:
        term1 = Term.objects.create(
            content="term1",
            slug="term1",
        )
        person3 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hg@magic.uk",
            username="hg",
        )
        consents = Consent.objects.filter(term=term1)
        self.assertEqual(len(consents), 3)

        consent1 = consents.filter(person=self.person1)[0]
        self.assertIsNone(consent1.term_option)
        self.assertIsNone(consent1.archived_at)

        consent2 = consents.filter(person=self.person2)[0]
        self.assertIsNone(consent2.term_option)
        self.assertIsNone(consent2.archived_at)

        consent3 = consents.filter(person=person3)[0]
        self.assertIsNone(consent3.term_option)
        self.assertIsNone(consent3.archived_at)

        # When person is updated consents do not change
        person3.middle = "middle"
        person3.save()

        consents = Consent.objects.filter(term=term1)
        self.assertEqual(len(consents), 3)

        consent1 = consents.filter(person=self.person1)[0]
        self.assertIsNone(consent1.term_option)
        self.assertIsNone(consent1.archived_at)

        consent2 = consents.filter(person=self.person2)[0]
        self.assertIsNone(consent2.term_option)
        self.assertIsNone(consent2.archived_at)

        consent3 = consents.filter(person=person3)[0]
        self.assertIsNone(consent3.term_option)
        self.assertIsNone(consent3.archived_at)

    def test_unset_consents_are_created_on_person_create_archived_term(self) -> None:
        term1 = Term.objects.create(
            content="term1", slug="term1", archived_at=timezone.now()
        )
        person3 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hg@magic.uk",
            username="hg",
        )
        consents = Consent.objects.filter(term=term1)
        self.assertEqual(len(consents), 3)

        consent1 = consents.filter(person=self.person1)[0]
        self.assertIsNone(consent1.term_option)
        self.assertEqual(consent1.archived_at, term1.archived_at)

        consent2 = consents.filter(person=self.person2)[0]
        self.assertIsNone(consent2.term_option)
        self.assertEqual(consent2.archived_at, term1.archived_at)

        consent3 = consents.filter(person=person3)[0]
        self.assertIsNone(consent3.term_option)
        self.assertEqual(consent3.archived_at, term1.archived_at)

        # When person is updated consents do not change
        person3.middle = "middle"
        person3.save()

        consents = Consent.objects.filter(term=term1)
        self.assertEqual(len(consents), 3)

        consent1 = consents.filter(person=self.person1)[0]
        self.assertIsNone(consent1.term_option)
        self.assertEqual(consent1.archived_at, term1.archived_at)

        consent2 = consents.filter(person=self.person2)[0]
        self.assertIsNone(consent2.term_option)
        self.assertEqual(consent2.archived_at, term1.archived_at)

        consent3 = consents.filter(person=person3)[0]
        self.assertIsNone(consent3.term_option)
        self.assertEqual(consent3.archived_at, term1.archived_at)
