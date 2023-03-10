from __future__ import annotations

from enum import StrEnum
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.functional import cached_property

from autoemails.mixins import RQJobsMixin
from workshops.mixins import CreatedUpdatedArchivedMixin
from workshops.models import STR_MED, Person


class TermQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(archived_at=None)

    def prefetch_active_options(self):
        return self._prefetch_options(TermOption.objects.active(), "active_options")

    def prefetch_all_options(self):
        return self._prefetch_options(TermOption.objects.all(), "all_options")

    def _prefetch_options(self, options_queryset, attr_name: str):
        return self.prefetch_related(
            Prefetch(
                "termoption_set",
                queryset=options_queryset,
                to_attr=attr_name,
            )
        )


class TermOptionQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(archived_at=None)


class ConsentQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(archived_at=None)


class TermEnum(StrEnum):
    """Base terms that were introduced via migration
    `amy/consents/migrations/0005_auto_20210411_2325.py`.

    They (used to) have corresponding flags in Person model."""

    MAY_PUBLISH_NAME = "may-publish-name"
    PUBLIC_PROFILE = "public-profile"
    MAY_CONTACT = "may-contact"
    PRIVACY_POLICY = "privacy-policy"


class Term(CreatedUpdatedArchivedMixin, RQJobsMixin, models.Model):
    PROFILE_REQUIRE_TYPE = "profile"
    OPTIONAL_REQUIRE_TYPE = "optional"
    TERM_REQUIRE_TYPE = (
        (PROFILE_REQUIRE_TYPE, "Required to create a Profile"),
        (OPTIONAL_REQUIRE_TYPE, "Optional"),
    )

    slug = models.SlugField(unique=True)
    content = models.TextField(verbose_name="Content")
    required_type = models.CharField(
        max_length=STR_MED, choices=TERM_REQUIRE_TYPE, default=OPTIONAL_REQUIRE_TYPE
    )
    help_text = models.TextField(verbose_name="Help Text", blank=True)
    objects = TermQuerySet.as_manager()

    @cached_property
    def options(self) -> Iterable[TermOption]:
        # If you've already prefetched active_options
        # Use that instead. Otherwise query for the options
        return getattr(self, "active_options", self._fetch_options())

    def _fetch_options(self) -> Iterable[TermOption]:
        return TermOption.objects.active().filter(term=self)

    def archive(self) -> None:
        """
        Archive the term. And archive all term options and consents with the given term.
        """
        self.archived_at = timezone.now()
        self.save()
        TermOption.objects.filter(term=self).active().update(
            archived_at=self.archived_at
        )
        Consent.objects.filter(term=self).active().update(archived_at=self.archived_at)

    def __str__(self) -> str:
        return self.slug

    def clean(self) -> None:
        is_required = self.required_type != self.OPTIONAL_REQUIRE_TYPE
        has_yes_option = False
        for option in self._fetch_options():
            if option.option_type == TermOptionChoices.AGREE:
                has_yes_option = True
        if is_required and self.archived_at is None and not has_yes_option:
            raise ValidationError(
                f"Required term {self} must have agree term option."
                " Please add a term option separately,"
                " and then change this term to required."
            )


class TermOptionChoices(models.TextChoices):
    AGREE = "agree", "Agree"
    DECLINE = "decline", "Decline"


class TermOption(CreatedUpdatedArchivedMixin, models.Model):

    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    option_type = models.CharField(
        max_length=STR_MED, choices=TermOptionChoices.choices
    )
    content = models.TextField(verbose_name="Content", blank=True)
    objects = TermOptionQuerySet.as_manager()

    def __str__(self):
        return f"{self.content} ({self.option_type})"

    def archive(self) -> None:
        """
        Archive self and archive all Consent objects that have the
        term option as their answer.

        If the Term this term option is attached to is still active,
        the user will be notified to reconsent.

        If the Term is required and the current term option is the only yes
        option raise an error.
        """
        self._check_is_only_agree_option_for_required_term()
        self.archived_at = timezone.now()
        self.save()
        Consent.objects.filter(term_option=self).active().update(
            archived_at=self.archived_at
        )

    def _check_is_only_agree_option_for_required_term(self) -> None:
        """
        Helper method for self.archive()

        If this term option is the only yes option for a required term,
        do not allow the user to archive the term option.
        """
        if (
            self.option_type == TermOptionChoices.AGREE
            and self.archived_at is None
            and self.term.required_type != self.term.OPTIONAL_REQUIRE_TYPE
            and self.term.archived_at is None
        ):
            num_agree_options = len(
                [
                    option
                    for option in self.term._fetch_options()
                    if option.option_type == TermOptionChoices.AGREE
                ]
            )
            if num_agree_options == 1:
                raise ValidationError(
                    f"Term option {self} is the only {TermOptionChoices.AGREE} term"
                    f" option for required term {self.term}. Please add an additional"
                    f" {TermOptionChoices.AGREE} option or archive the term instead."
                )


class Consent(CreatedUpdatedArchivedMixin, models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.PROTECT)
    term_option = models.ForeignKey(TermOption, on_delete=models.PROTECT, null=True)
    objects = ConsentQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["person", "term"],
                name="person__term__unique__when__archived_at__null",
                condition=models.Q(archived_at__isnull=True),
            ),
        ]

    def save(self, *args, **kwargs):
        if self.term_option and self.term.pk != self.term_option.term.pk:
            raise ValidationError("Consent term.id must match term_option.term_id")
        return super().save(*args, **kwargs)

    @classmethod
    def create_unset_consents_for_term(cls, term: Term) -> None:
        """
        Creates unset consents for all users with the given term.

        Used when a term is first created so that unset consents
        are stored in the database for any given term.
        """
        cls.objects.bulk_create(
            cls(
                person=person,
                term=term,
                term_option=None,
            )
            for person in Person.objects.all()
        )

    def archive(self) -> None:
        self.archived_at = timezone.now()
        self.save()

    @classmethod
    def archive_all_for_term(cls, terms: Iterable[Term]) -> None:
        consents = cls.objects.filter(term__in=terms).active()
        cls.archive_all(consents)

    @classmethod
    def archive_all_for_person(cls, person: Person):
        consents = cls.objects.filter(person=person).active()
        cls.archive_all(consents)

    @classmethod
    def archive_all(cls, consents: models.query.QuerySet[Consent]) -> None:
        new_consents = [
            cls(
                person_id=consent.person.pk,
                term_id=consent.term.pk,
                term_option=None,
            )
            for consent in consents
        ]
        consents.update(archived_at=timezone.now())
        cls.objects.bulk_create(new_consents)

    @classmethod
    def reconsent(cls, consent: Consent, term_option: TermOption) -> Consent:
        consent.archive()
        return Consent.objects.create(
            term_id=term_option.term.pk,
            term_option=term_option,
            person_id=consent.person.pk,
        )
