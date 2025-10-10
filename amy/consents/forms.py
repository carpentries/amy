from typing import Any, Iterable, List

from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH

from consents.models import Consent, Term, TermOption, TermOptionChoices
from workshops.forms import BootstrapHelper, WidgetOverrideMixin
from workshops.models import Person

OPTION_DISPLAY = {
    TermOptionChoices.AGREE: "Yes",
    TermOptionChoices.DECLINE: "No",
}


def option_display_value(option: TermOption) -> str:
    return option.content or OPTION_DISPLAY[TermOptionChoices(option.option_type)]


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
            self.fields[term.slug] = self.create_options_field(term)

    def create_options_field(self, term: Term) -> forms.ChoiceField:
        consent = self.term_id_by_consent.get(term.pk, None)
        options = [(opt.pk, option_display_value(opt)) for opt in term.options]
        required = term.required_type != Term.OPTIONAL_REQUIRE_TYPE
        initial = consent.term_option_id if consent else None
        attrs = {"class": "border border-warning"} if initial is None else {}

        field = forms.ChoiceField(
            choices=BLANK_CHOICE_DASH + options,  # type: ignore
            label=term.content,
            required=required,
            initial=initial,
            help_text=term.help_text,
            widget=forms.Select(attrs=attrs),
        )
        return field

    def save(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        person = self.cleaned_data["person"]
        new_consents: List[Consent] = []
        for term in self.terms:
            option_id = self.cleaned_data.get(term.slug)
            consent = self.term_id_by_consent.get(term.pk)
            has_changed = option_id != str(consent.term_option_id) if consent else True
            if not option_id or not has_changed:
                continue
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

    def get_terms(self) -> Iterable[Term]:
        return Term.objects.active().prefetch_active_options().filter(required_type=Term.PROFILE_REQUIRE_TYPE)


class TermBySlugsForm(BaseTermConsentsForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.term_slugs = kwargs.pop("term_slugs")
        super().__init__(*args, **kwargs)

    def get_terms(self) -> Iterable[Term]:
        return Term.objects.active().prefetch_active_options().filter(slug__in=self.term_slugs)
