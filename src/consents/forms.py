from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from django import forms
from django.db.models import QuerySet
from django.db.models.fields import BLANK_CHOICE_DASH

from src.consents.models import BaseConsent, Consent, Term, TermOption, TermOptionChoices
from src.workshops.forms import BootstrapHelper, WidgetOverrideMixin
from src.workshops.models import Person

OPTION_DISPLAY = {
    TermOptionChoices.AGREE: "Yes",
    TermOptionChoices.DECLINE: "No",
}


def option_display_value(option: TermOption) -> str:
    return option.content or OPTION_DISPLAY[TermOptionChoices(option.option_type)]


def create_consent_field(
    term: Term,
    consent: BaseConsent | None = None,
    *,
    label: str | None = None,
    required: bool | None = None,
) -> forms.ChoiceField:
    """Build a select field with the term's options. The current consent (if any) is
    used as the initial value. By default the label is the term's content and the field
    is required for non-optional terms."""
    options = [(opt.pk, option_display_value(opt)) for opt in term.options]
    initial = consent.term_option_id if consent else None
    attrs = {"class": "border border-warning"} if initial is None else {}

    return forms.ChoiceField(
        choices=BLANK_CHOICE_DASH + options,  # type: ignore[operator]
        label=term.content if label is None else label,
        required=term.required_type != Term.OPTIONAL_REQUIRE_TYPE if required is None else required,
        initial=initial,
        help_text=term.help_text or "",
        widget=forms.Select(attrs=attrs),
    )


def changed_consents[C: BaseConsent](
    terms: Iterable[Term],
    cleaned_data: Mapping[str, Any],
    current_consents: Mapping[int, C],
) -> Iterator[tuple[Term, str, C | None]]:
    """Yield `(term, selected option ID, current consent)` for every term whose answer
    (a form field named after the term's slug) differs from the current consent.
    Terms left blank are skipped. `current_consents` maps term IDs to active consents."""
    for term in terms:
        option_id = cleaned_data.get(term.slug)
        consent = current_consents.get(term.pk)
        if not option_id or (consent and option_id == str(consent.term_option_id)):
            continue
        yield term, option_id, consent


class BaseTermConsentsForm(WidgetOverrideMixin, forms.ModelForm[Consent]):
    """
    Builds form including all active terms with
    the provided person's consents as the initial selection.

    Saves the user's responses as Consent models.
    """

    class Meta:
        model = Consent
        fields = ["person"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        form_tag = kwargs.pop("form_tag", True)
        self.person = kwargs["initial"]["person"]
        super().__init__(*args, **kwargs)
        self.terms = self.get_terms()
        self._build_form(self.person)
        self.helper = BootstrapHelper(
            add_cancel_button=False,
            form_tag=form_tag,
            wider_labels=True,
        )

    def _build_form(self, person: Person) -> None:
        """
        Construct a Form of terms with the
        consent answers added as initial.
        """

        self.term_id_by_consent = {
            consent.term_id: consent
            for consent in Consent.objects.filter(archived_at=None, term__in=self.terms, person=person)
        }
        for term in self.terms:
            self.fields[term.slug] = create_consent_field(term, self.term_id_by_consent.get(term.pk))

    def save(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        person = self.cleaned_data["person"]
        new_consents: list[Consent] = []
        for term, option_id, consent in changed_consents(self.terms, self.cleaned_data, self.term_id_by_consent):
            if consent:
                consent.archive()
            new_consents.append(Consent(person=person, term_option_id=option_id, term_id=term.pk))
        Consent.objects.bulk_create(new_consents)

    def get_terms(self) -> Iterable[Term]:
        return Term.objects.all().prefetch_active_options()


class ActiveTermConsentsForm(BaseTermConsentsForm):
    """
    Builds form with all active terms.
    """

    def get_terms(self) -> Iterable[Term]:
        return Term.objects.active().prefetch_active_options()


class RequiredConsentsForm(BaseTermConsentsForm):
    """
    Builds form shown on login when there are missing required consents.
    """

    def _build_form(self, person: Person) -> None:
        """
        Construct a Form of terms with the
        consent answers added as initial.

        Filter terms to only those that have not been answered by the person.
        """
        term_ids = Consent.objects.filter(
            archived_at=None, term__in=self.terms, person=person, term_option=None
        ).values_list("term_id", flat=True)
        self.terms = [term for term in self.terms if term.id in term_ids]
        super()._build_form(person)

    def get_terms(self) -> QuerySet[Term]:
        return Term.objects.active().prefetch_active_options().filter(required_type=Term.PROFILE_REQUIRE_TYPE)


class TermBySlugsForm(BaseTermConsentsForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.term_slugs = kwargs.pop("term_slugs")
        super().__init__(*args, **kwargs)

    def get_terms(self) -> QuerySet[Term]:
        return Term.objects.active().prefetch_active_options().filter(slug__in=self.term_slugs)
