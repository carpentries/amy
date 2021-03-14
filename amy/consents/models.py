from django.db import models
from workshops.mixins import CreatedUpdatedMixin
from workshops.models import Person, STR_MED
from django.db.models import Prefetch
from django.core.exceptions import ValidationError


class CreatedUpdatedArchivedMixin(CreatedUpdatedMixin):
    """This mixin adds an archived timestamp to the CreatedUpdatedMixin."""

    archived_at = models.DateTimeField(null=True)

    class Meta:
        abstract = True


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


class TermOption(CreatedUpdatedArchivedMixin, models.Model):
    AGREE = "agree"
    DECLINE = "decline"
    UNSET = "unset"
    OPTION_TYPE = ((AGREE, "Agree"), (DECLINE, "Decline"), (UNSET, "Unset"))

    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    option_type = models.CharField(max_length=STR_MED, choices=OPTION_TYPE)
    content = models.TextField(verbose_name="Content", blank=True)
    objects = TermOptionQuerySet.as_manager()


class Consent(CreatedUpdatedArchivedMixin, models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.PROTECT)
    term_option = models.ForeignKey(TermOption, on_delete=models.PROTECT)
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
        return super().save(*args, **kwargs)
