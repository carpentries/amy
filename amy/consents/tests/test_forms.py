from consents.forms import ActiveTermConsentsForm
from consents.models import Consent, Term, TermOption
from django.test import TestCase
from django.utils import timezone
from workshops.models import Person


class TestTermForm(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )

    def test_init_creates_term_fields(self) -> None:
        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type=TermOption.AGREE,
            content="term1_option1",
        )
        term1_option2 = TermOption.objects.create(
            term=term1,
            option_type=TermOption.DECLINE,
            content="term1_option2",
        )
        term2 = Term.objects.create(content="term2", slug="term2")
        term2_option1 = TermOption.objects.create(
            term=term2,
            option_type=TermOption.AGREE,
        )
        term2_option2 = TermOption.objects.create(
            term=term2,
            option_type=TermOption.DECLINE,
        )
        Consent.objects.create(
            person=self.person,
            term=term1,
            term_option=term1_option1,
        )
        form = ActiveTermConsentsForm(person=self.person)
        self.assertIn(term1.slug, form.fields)
        self.assertCountEqual(
            form.fields[term1.slug].choices,
            [
                (term1_option1.id, "term1_option1"),
                (term1_option2.id, "term1_option2"),
            ],
        )
        self.assertIn(term2.slug, form.fields)
        self.assertCountEqual(
            form.fields[term2.slug].choices,
            [
                (term2_option1.id, "Yes"),
                (term2_option2.id, "No"),
            ],
        )

    def test_init_omits_archived_terms(self) -> None:
        term1 = Term.objects.create(
            content="term1", slug="term1", archived_at=timezone.now()
        )
        TermOption.objects.create(
            term=term1,
            option_type=TermOption.AGREE,
            content="term1_option1",
            archived_at=timezone.now(),
        )
        form = ActiveTermConsentsForm(person=self.person)
        self.assertNotIn(term1.slug, form.fields)
