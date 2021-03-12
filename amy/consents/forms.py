from typing import List

from consents.models import Consent, Term, TermOption
from django import forms
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


class ActiveTermConsentsForm(WidgetOverrideMixin, forms.ModelForm):
    """
    Builds form including all active terms with
    the provided person's consents as the initial selection.
    Saves Consent models.
    """

    class Meta:
        model = Consent
        fields = ["person"]

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        person = kwargs.pop("person")
        super().__init__(*args, **kwargs)
        self._build_form(person)
        self.helper = BootstrapHelper(add_cancel_button=False, form_tag=form_tag)

    def _build_form(self, person: Person) -> None:
        """
        Construct a Form of terms with the
        consent answers added as initial.
        """
        self.terms = Term.objects.active().prefetch_active_options()
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
            widget=forms.RadioSelect,
            choices=options,
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
            if not option_id:
                continue
            consent = self.term_id_by_consent.get(term.id)
            if consent:
                consent.archived_at = timezone.now()
                consent.save()
            new_consents.append(
                Consent(person=person, term_option_id=option_id, term_id=term.id)
            )
        Consent.objects.bulk_create(new_consents)
