from typing import Sequence

from django import template

from consents.models import Consent, TermEnum, TermOptionChoices

register = template.Library()


@register.simple_tag
def consent_agreed(consents: Sequence[Consent], term: TermEnum) -> bool:
    return next(
        (
            consent.term_option.option_type == TermOptionChoices.AGREE
            for consent in consents
            if consent.term_option and consent.term.slug == term
        ),
        False,
    )


@register.simple_tag
def consent_declined(consents: Sequence[Consent], term: TermEnum) -> bool:
    return next(
        (
            consent.term_option.option_type == TermOptionChoices.DECLINE
            for consent in consents
            if consent.term_option and consent.term.slug == term
        ),
        False,
    )
