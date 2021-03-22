from __future__ import annotations
from django.db import models
from workshops.mixins import CreatedUpdatedMixin
from workshops.models import Person, STR_MED
from django.db.models import Prefetch
from django.core.exceptions import ValidationError
from django.utils import timezone


class CreatedUpdatedArchivedMixin(CreatedUpdatedMixin):
    """This mixin adds an archived timestamp to the CreatedUpdatedMixin."""

    archived_at = models.DateTimeField(null=True)

    class Meta:
        abstract = True

    def archive(self):
        self.archived_at = timezone.now()
        self.save()


class TermQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(archived_at=None)

    def prefetch_active_options(self):
        return self._prefetch_options(TermOption.objects.active())

    def prefetch_all_options(self):
        return self._prefetch_options(TermOption.objects.all())

    def _prefetch_options(self, options_queryset):
        return self.prefetch_related(
            Prefetch(
                "termoption_set",
                queryset=options_queryset,
                to_attr="options",
            )
        )


class TermOptionQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(archived_at=None)


class ConsentQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(archived_at=None)

    # def from_terms_and_person(self, terms: Iterable[Term], person: Person):
    #     """
    #     Retrive a list of consents from the given Person.
    #     # TODO: I think originally I thought about
    #     # saving unset values for all users on term create
    #     # but I'm realizing that might not be necessary.
    #     # That said if I store unset values for all users,
    #     # this query will not be necessary.
    #     """
    #     queryset = self.filter(person=person, term__in=terms)
    #     set(self.filter(person=person, term__in=terms).values)
    #     for term in terms:
    #         if

    # def terms_not_consented_to(self, terms: Iterable[Term], person: Person):
    #     self.filter(
    #         ~Exists(
    #             Consents.object.filter(person=


class Term(CreatedUpdatedArchivedMixin, models.Model):
    PROFILE_REQUIRE_TYPE = "profile"
    OPTIONAL_REQUIRE_TYPE = "optional"
    TERM_REQUIRE_TYPE = (
        (PROFILE_REQUIRE_TYPE, "Required to create a Profile"),
        (OPTIONAL_REQUIRE_TYPE, "Optional"),
    )

    slug = models.SlugField(unique=True)
    content = models.TextField(verbose_name="Content")
    help_text = models.TextField(verbose_name="Help Text", blank=True)
    required_type = models.CharField(
        max_length=STR_MED, choices=TERM_REQUIRE_TYPE, default=OPTIONAL_REQUIRE_TYPE
    )
    objects = TermQuerySet.as_manager()

    def save(self, *args, **kwargs):
        # If we are adding a new Term, create unset consent objects for all users.
        result = super().save(*args, **kwargs)
        if self._state.adding:
            Consent.create_unset_consents_for_term(self)
        return result


class TermOption(CreatedUpdatedArchivedMixin, models.Model):
    AGREE = "agree"
    DECLINE = "decline"
    OPTION_TYPE = ((AGREE, "Agree"), (DECLINE, "Decline"))

    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    option_type = models.CharField(max_length=STR_MED, choices=OPTION_TYPE)
    content = models.TextField(verbose_name="Content", blank=True)
    objects = TermOptionQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self.content:
            if self.option_type == self.AGREE:
                self.content = "Yes"
            elif self.option_type == self.DECLINE:
                self.content = "No"
            else:  # TODO: should this even be possible?
                raise ValueError(
                    "TermOption content not defined"
                    f" and option_type not in {self.OPTION_TYPE}."
                )
        return super().save(*args, **kwargs)


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
        if self.term_id != self.term_option.term_id:
            raise ValidationError("Consent term.id must match term_option.term_id")

        # Archive old consent if user has consented previously.
        try:
            prev_consent = Consent.objects.get(
                person=self.person, term=self.term, archived_at=None
            )
        except Consent.DoesNotExist:
            pass
        else:
            prev_consent.archive()

        return super().save(*args, **kwargs)

    @classmethod
    def create_unset_consents_for_term(cls, term: Term) -> None:
        consents = [
            cls(
                person=person,
                term=term,
                term_option=None,
            )
            for person in Person.objects.all()
        ]
        cls.objects.bulk_create(consents)
