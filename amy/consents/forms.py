from typing import Iterable, List

from consents.models import Consent, Term, TermOption
from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from django.utils import timezone
from workshops.forms import BootstrapHelper, WidgetOverrideMixin
from workshops.models import Person

OPTION_DISPLAY = {
    TermOption.AGREE: "Yes",
    TermOption.DECLINE: "No",
    TermOption.UNSET: "unset",
}


def option_display_value(option: TermOption) -> str:
    return option.content or OPTION_DISPLAY[option.option_type]


class BaseTermConsentsForm(WidgetOverrideMixin, forms.ModelForm):
    """
    Builds form including all active terms with
    the provided person's consents as the initial selection.

    Saves the user's responses as Consent models.
    """

    class Meta:
        model = Consent
        fields = ["person"]

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        person = kwargs["initial"]["person"]
        super().__init__(*args, **kwargs)
        self.terms = self.get_terms()
        self._build_form(person)
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
            for consent in Consent.objects.filter(
                archived_at=None, term__in=self.terms, person=person
            )
        }
        for term in self.terms:
            self.fields[term.slug] = self.create_options_field(term)

    def create_options_field(self, term: Term):
        consent = self.term_id_by_consent.get(term.id, None)
        options = [(opt.id, option_display_value(opt)) for opt in term.options]
        required = term.required_type != Term.OPTIONAL_REQUIRE_TYPE
        field = forms.ChoiceField(
            choices=BLANK_CHOICE_DASH + options,
            label=term.content,
            required=required,
            initial=consent.term_option_id if consent else None,
        )
        return field

    def save(self, *args, **kwargs):
        person = self.cleaned_data["person"]
        new_consents: List[Consent] = []
        for term in self.terms:
            option_id = self.cleaned_data.get(term.slug)
            consent = self.term_id_by_consent.get(term.id)
            has_changed = option_id != str(consent.term_option_id) if consent else True
            if not option_id or not has_changed:
                continue
            if consent:
                consent.archived_at = timezone.now()
                consent.save()
            new_consents.append(
                Consent(person=person, term_option_id=option_id, term_id=term.id)
            )
        Consent.objects.bulk_create(new_consents)

    @classmethod
    def get_terms(cls) -> Iterable[Term]:
        return Term.objects.all().prefetch_active_options()


class ActiveTermConsentsForm(BaseTermConsentsForm):
    """
    Builds form with all active terms.
    """

    @classmethod
    def get_terms(cls) -> Iterable[Term]:
        return Term.objects.active().prefetch_active_options()


class RequiredConsentsForm(BaseTermConsentsForm):
    """
    Builds form shown on login when there are missing required consents.
    """

    @classmethod
    def get_terms(cls) -> Iterable[Term]:
        return (
            Term.objects.active()
            .prefetch_active_options()
            .filter(required_type=Term.PROFILE_REQUIRE_TYPE)
        )
