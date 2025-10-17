from datetime import date

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Manager, Q, QuerySet
from django.urls import reverse
from django_better_admin_arrayfield.models.fields import ArrayField

from workshops.mixins import CreatedUpdatedMixin
from workshops.models import Award, Badge, Membership, Person


class CommunityRoleConfig(CreatedUpdatedMixin, models.Model):
    name = models.CharField(max_length=150)
    display_name = models.CharField(max_length=150)
    link_to_award = models.BooleanField("Should link to an Award?")
    award_badge_limit = models.ForeignKey(
        Badge,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    autoassign_when_award_created = models.BooleanField(
        "Auto-assign when award is created",
        default=False,
        help_text="Should automatically assign a Community Role to a user, when "
        "a selected badge is awarded to them.",
    )
    link_to_membership = models.BooleanField("Should link to a Membership?")
    additional_url = models.BooleanField("Should allow for additional URL?")
    generic_relation_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    custom_key_labels = ArrayField(
        models.CharField(max_length=150),
        help_text="Labels to be used for custom text fields in community roles.",
        default=list,
        blank=True,
    )

    def __str__(self) -> str:
        return self.display_name


class CommunityRoleInactivation(CreatedUpdatedMixin, models.Model):
    name = models.CharField(max_length=150)

    def __str__(self) -> str:
        return self.name


class CommunityRoleQuerySet(QuerySet["CommunityRole"]):
    def active(self) -> QuerySet["CommunityRole"]:
        today = date.today()
        return self.filter(
            Q(inactivation__isnull=True)
            & (Q(start__isnull=False) & Q(start__lt=today) | Q(start__isnull=True))
            & (Q(end__isnull=False) & Q(end__gte=today) | Q(end__isnull=True))
        )


class CommunityRole(CreatedUpdatedMixin, models.Model):
    config = models.ForeignKey(CommunityRoleConfig, on_delete=models.PROTECT, verbose_name="Role Name")
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    award = models.ForeignKey(
        Award,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Associated Award",
    )
    start = models.DateField(null=True, blank=False, verbose_name="Role Start Date")
    end = models.DateField(null=True, blank=True, verbose_name="Role End Date")
    inactivation = models.ForeignKey(
        CommunityRoleInactivation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Reason for inactivation",
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Associated Membership",
    )
    url = models.URLField("URL", blank=True, default="")

    # value should be copied from related `CommunityRoleConfig`
    generic_relation_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    generic_relation_pk = models.PositiveIntegerField(null=True, blank=True)
    generic_relation = GenericForeignKey("generic_relation_content_type", "generic_relation_pk")

    # Store custom keys (as defined by CommunityRoleConfig.custom_key_labels) in a list
    # of pairs like so:
    # [
    #   ("This is a label for a key", "This is a value."),
    #   ("Website", "https://carpentries.org/"),
    # ]
    custom_keys = models.JSONField(default=str, blank=True, null=True)

    objects = Manager.from_queryset(CommunityRoleQuerySet)()

    def __str__(self) -> str:
        return f'Community Role "{self.config}" for {self.person}'

    def get_absolute_url(self) -> str:
        return reverse("communityrole_details", kwargs={"pk": self.pk})

    def is_active(self) -> bool:
        """Determine if a community role is considered active.

        Rules for INACTIVE:
        1. `inactivation` is provided, or...
        2. End is provided and it's <= today, or...
        3. Start is provided and it's > today, or...
        4. Both start and end are provided, and today is NOT between them.

        Otherwise by default it's ACTIVE."""
        today = date.today()
        if (
            self.inactivation is not None
            or (self.end and self.end <= today)
            or (self.start and self.start > today)
            or (self.start and self.end and not (self.start <= today < self.end))
        ):
            return False
        return True
