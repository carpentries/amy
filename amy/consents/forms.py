from typing import Iterable
from consents.models import Consent
from django import forms
from workshops.forms import BootstrapHelper
from consents.models import Term, TermOption
from workshops.forms import WidgetOverrideMixin
from workshops.models import Person
from django.utils import timezone


OPTION_DISPLAY = {
    TermOption.AGREE: "Yes",
    TermOption.DECLINE: "No",
}


def option_display_value(option: TermOption) -> str:
    return option.content or OPTION_DISPLAY[option.option_type]


class ConsentsForm(WidgetOverrideMixin, forms.ModelForm):
    class Meta:
        model = Consent
        fields = []

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        person = kwargs.pop("person")
        super().__init__(*args, **kwargs)
        self._build_form(person)
        self.helper = BootstrapHelper(add_cancel_button=False, form_tag=form_tag)

    def _build_form(self, person: Person) -> None:
        """
        Construct a Form of all nonarchived Terms with the
        consent answers added as initial.
        """
        self.terms = Term.objects.active().prefetch_active_options()
        term_id_by_option_id = {
            consent.term_id: consent.term_option_id
            for consent in Consent.objects.filter(
                archived_at=None, term__in=self.terms, person=person
            )
        }
        for term in self.terms:
            self.fields[term.slug] = self.create_options_field(
                term=term,
                options=term.options,
                selected=term_id_by_option_id.get(term.id, None),
            )

    def create_options_field(
        self, term: Term, options: Iterable[TermOption], selected=None
    ):
        options = [(opt.id, option_display_value(opt)) for opt in options]
        required = False if term.required_type == Term.OPTIONAL_REQUIRE_TYPE else True
        field = forms.ChoiceField(
            widget=forms.RadioSelect,
            choices=options,
            label=term.content,
            required=required,
            initial=selected,
        )
        return field

    def save(self, *args, **kwargs):
        person = self.cleaned_data["person"]
        for term in self.terms:
            option_id = self.cleaned_data.get(term.slug)
            if not option_id:
                continue
            try:
                consent = Consent.objects.get(
                    person=person, term=term, archived_at=None
                )
            except Consent.DoesNotExist:
                pass
            else:
                consent.archived_at = timezone.now()
                consent.save()
            Consent.objects.create(
                person=person, term_option_id=option_id, term_id=term.id
            )

    def _yes_only(self, term) -> bool:
        return len(term.options) == 1

    def _yes_and_no(self, term) -> bool:
        return len(term.options) == 2
