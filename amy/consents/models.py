from functools import cached_property

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch
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

    @cached_property
    def is_yes_only(self) -> bool:
        options = self.options
        return len(options) == 1 and options[0].option_type == TermOption.AGREE

    @cached_property
    def is_yes_and_no(self) -> bool:
        if len(self.options) != 2:
            return False

        option_types = set([option.option_type for option in self.options])
        return option_types == set([TermOption.AGREE, TermOption.DECLINE])


class TermOption(CreatedUpdatedArchivedMixin, models.Model):
    AGREE = "agree"
    DECLINE = "decline"
    UNSET = "unset"
    OPTION_TYPE = ((AGREE, "Agree"), (DECLINE, "Decline"), (UNSET, "Unset"))

    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    option_type = models.CharField(max_length=STR_MED, choices=OPTION_TYPE)
    content = models.TextField(verbose_name="Content", blank=True)
    objects = TermOptionQuerySet.as_manager()

    def __str__(self):
        return f"{self.content} ({self.option_type})"


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


def create_yes_only_term(
    *, slug: str, content: str, required_type: str = Term.OPTIONAL_REQUIRE_TYPE
) -> Term:
    term = Term.objects.create(
        slug=slug,
        content=content,
        required_type=required_type,
    )
    TermOption.objects.create(
        term=term,
        option_type=TermOption.AGREE,
    )
    return term


def create_yes_and_no_term(
    *, slug: str, content: str, required_type: str = Term.OPTIONAL_REQUIRE_TYPE
) -> Term:
    term = create_yes_only_term(slug=slug, content=content, required_type=required_type)
    TermOption.objects.create(
        term=term,
        option_type=TermOption.DISAGREE,
    )
