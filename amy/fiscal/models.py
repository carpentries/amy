from django.db import models

from workshops.consts import STR_LONG, STR_LONGEST
from workshops.models import Membership, Person


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


class Consortium(models.Model):
    """New model representing a consortium of multiple organisations.
    Part of Service Offering 2025 project."""

    name = models.CharField(max_length=STR_LONG)
    description = models.CharField(max_length=STR_LONGEST)

    def __str__(self) -> str:
        return self.name
