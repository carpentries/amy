import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.urls import reverse

from workshops.consts import STR_LONG, STR_LONGEST, STR_MED
from workshops.mixins import CreatedUpdatedMixin
from workshops.models import Membership, Organization, Person
from workshops.utils.dates import human_daterange


class MembershipPersonRole(models.Model):
    """People roles in memberships."""

    name = models.CharField(max_length=40)
    verbose_name = models.CharField(max_length=100, null=False, blank=True, default="")

    def __str__(self) -> str:
        return self.verbose_name


class MembershipTask(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    role = models.ForeignKey(MembershipPersonRole, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("membership", "person", "role")
        ordering = ("role__name", "membership")

    def __str__(self) -> str:
        return f"{self.role} {self.person} ({self.membership})"


class Consortium(CreatedUpdatedMixin, models.Model):
    """New model representing a consortium of multiple organisations.
    Part of Service Offering 2025 project."""

    name = models.CharField(max_length=STR_LONG)
    description = models.CharField(max_length=STR_LONGEST)
    organisations = models.ManyToManyField(Organization)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("consortium-details", kwargs={"pk": self.pk})


class PartnershipTier(CreatedUpdatedMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=STR_LONG, blank=False, null=False)

    def __str__(self) -> str:
        return self.name


class Partnership(CreatedUpdatedMixin, models.Model):
    """A follow-up to "Membership" model, part of Service Offering 2025 project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=STR_LONG)
    tier = models.ForeignKey(PartnershipTier, on_delete=models.SET_NULL, null=True, blank=True)

    agreement_start = models.DateField()
    agreement_end = models.DateField(
        help_text="If an extension is being granted, do not manually edit the end date."
        ' Use the "Extend" button on partnership details page instead.'
    )
    extensions = ArrayField(
        models.PositiveIntegerField(),
        help_text="Number of days the agreement was extended. The field stores "
        "multiple extensions. The agreement end date has been moved by a cumulative "
        "number of days from this field.",
        default=list,
    )
    rolled_to_partnership = models.OneToOneField(
        "Partnership",
        on_delete=models.SET_NULL,
        related_name="rolled_from_partnership",
        null=True,
    )

    agreement_link = models.URLField(
        blank=False,
        default="",
        verbose_name="Link to partnership agreement",
        help_text="Link to partnership agreement document or folder in Google Drive",
    )

    registration_code = models.CharField(
        max_length=STR_MED,
        null=True,
        blank=True,
        unique=True,
        verbose_name="Registration Code",
        help_text="Unique registration code used for Eventbrite and trainee application.",
    )

    PUBLIC_STATUS_CHOICES = (
        ("public", "Public"),
        ("private", "Private"),
    )
    public_status = models.CharField(
        max_length=20,
        choices=PUBLIC_STATUS_CHOICES,
        default=PUBLIC_STATUS_CHOICES[1][0],
        verbose_name="Can this partnership be publicized on The carpentries websites?",
        help_text="Public partnerships may be listed on any of The Carpentries websites.",
    )

    partner_consortium = models.ForeignKey(
        Consortium,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="Only consortium or organisation can be selected, never both.",
    )
    partner_organisation = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="Only consortium or organisation can be selected, never both.",
    )

    class Meta:
        # Ensure only 1 partner is selected, either consortium or organization.
        # TODO: different arguments in Django 5.2
        constraints = [
            models.CheckConstraint(
                check=Q(partner_consortium__isnull=True) ^ Q(partner_organisation__isnull=True),
                name="check_only_one_partner",
                violation_error_message="Select only partner consortium OR partner organisation, never both.",
            )
        ]

    def __str__(self) -> str:
        dates = human_daterange(self.agreement_start, self.agreement_end)
        tier = (self.tier.name if self.tier else "(no tier)").title()

        if self.partner_consortium:
            return f"{self.name} {tier} partnership {dates} (consortium)"
        else:
            return f"{self.name} {tier} partnership {dates}"

    def get_absolute_url(self) -> str:
        return reverse("partnership-details", kwargs={"pk": self.pk})
