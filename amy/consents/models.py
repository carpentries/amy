from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.functional import cached_property

from autoemails.mixins import RQJobsMixin
from workshops.mixins import CreatedUpdatedMixin
from workshops.models import STR_MED, Person


class CreatedUpdatedArchivedMixin(CreatedUpdatedMixin):
    """This mixin adds an archived timestamp to the CreatedUpdatedMixin."""

    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True


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
        # If you've already prefetched_active_options
        # Use that instead. Otherwise query for the options
        if hasattr(self, "active_options"):
            return self.active_options
        return self._fetch_options()

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
            if option.option_type == option.AGREE:
                has_yes_option = True
        if is_required and self.archived_at is None and not has_yes_option:
            raise ValidationError(
                f"Required term {self} must have agree term option."
                " Please add a term option separately,"
                " and then change this term to required."
            )


class TermOption(CreatedUpdatedArchivedMixin, models.Model):
    AGREE = "agree"
    DECLINE = "decline"
    OPTION_TYPE = ((AGREE, "Agree"), (DECLINE, "Decline"))

    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    option_type = models.CharField(max_length=STR_MED, choices=OPTION_TYPE)
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
            self.option_type == self.AGREE
            and self.archived_at is None
            and self.term.required_type != self.term.OPTIONAL_REQUIRE_TYPE
            and self.term.archived_at is None
        ):
            num_agree_options = len(
                [
                    option
                    for option in self.term._fetch_options()
                    if option.option_type == self.AGREE
                ]
            )
            if num_agree_options == 1:
                raise ValidationError(
                    f"Term option {self} is the only {self.AGREE} term option for"
                    f" required term {self.term}. Please add an additional"
                    f" {self.AGREE} option or archive the term instead."
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
        if self.term_option and self.term_id != self.term_option.term_id:
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
        new_consents = [
            cls(
                person=consent.person,
                term=consent.term,
                term_option=None,
            )
            for consent in consents
        ]
        consents.update(archived_at=timezone.now())
        cls.objects.bulk_create(new_consents)
