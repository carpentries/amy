from django.db.models.fields import BLANK_CHOICE_DASH
from django.utils import timezone

from consents.forms import ActiveTermConsentsForm, RequiredConsentsForm
from consents.models import Term, TermOption, TermOptionChoices
from consents.tests.base import ConsentTestBase
from workshops.models import Person


class TestActiveTermConsentsForm(ConsentTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.person = Person.objects.create(personal="Harry", family="Potter", email="hp@magic.uk")

    def test_init_creates_term_fields(self) -> None:
        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type=TermOptionChoices.AGREE,
            content="term1_option1",
        )
        term1_option2 = TermOption.objects.create(
            term=term1,
            option_type=TermOptionChoices.DECLINE,
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
        self.reconsent(
            person=self.person,
            term=term1,
            term_option=term1_option1,
        )
        form = ActiveTermConsentsForm(initial={"person": self.person})
        self.assertIn(term1.slug, form.fields)
        self.assertCountEqual(
            form.fields[term1.slug].choices,
            BLANK_CHOICE_DASH
            + [
                (term1_option1.id, "term1_option1"),
                (term1_option2.id, "term1_option2"),
            ],
        )
        self.assertIn(term2.slug, form.fields)
        self.assertCountEqual(
            form.fields[term2.slug].choices,
            BLANK_CHOICE_DASH
            + [
                (term2_option1.id, "Yes"),
                (term2_option2.id, "No"),
            ],
        )

    def test_init_omits_archived_terms(self) -> None:
        term1 = Term.objects.create(content="term1", slug="term1", archived_at=timezone.now())
        form = ActiveTermConsentsForm(initial={"person": self.person})
        self.assertNotIn(term1.slug, form.fields)


class TestRequiredConsentsForm(ConsentTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.person = Person.objects.create(personal="Harry", family="Potter", email="hp@magic.uk")

    def test_required_consent_form(self) -> None:
        required_term = Term.objects.create(
            content="required_term",
            slug="required_term",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        not_required_term = Term.objects.create(
            content="not_required_term",
            slug="not_required_term",
            required_type=Term.OPTIONAL_REQUIRE_TYPE,
        )
        archived_term = Term.objects.create(
            content="archived_term",
            slug="archived_term",
            archived_at=timezone.now(),
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        answered_required_term = Term.objects.create(
            content="answered_required_term",
            slug="answered_required_term",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        answered_required_term_yes = TermOption.objects.create(
            term=answered_required_term,
            option_type=TermOptionChoices.AGREE,
            content="Yes",
        )
        self.reconsent(self.person, answered_required_term, answered_required_term_yes)
        form = RequiredConsentsForm(initial={"person": self.person})
        self.assertIn(required_term.slug, form.fields)
        self.assertNotIn(not_required_term.slug, form.fields)
        self.assertNotIn(archived_term.slug, form.fields)
        # Already answered terms are filtered out
        self.assertNotIn(answered_required_term.slug, form.fields)
