from __future__ import annotations
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch
from django.utils.functional import cached_property
from django.utils import timezone

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


class Term(CreatedUpdatedArchivedMixin, models.Model):
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
    objects = TermQuerySet.as_manager()

    @cached_property
    def options(self):
        # If you've already prefetched_active_options
        # Use that instead. Otherwise query for the options
        if hasattr(self, "active_options"):
            return self.active_options
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
        """
        self.archived_at = timezone.now()
        self.save()
        Consent.objects.filter(term_option=self).active().update(
            archived_at=self.archived_at
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
