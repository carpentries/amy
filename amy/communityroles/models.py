from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse

from fiscal.models import Membership
from workshops.mixins import CreatedUpdatedMixin
from workshops.models import Award, Person, Role


class CommunityRoleConfig(CreatedUpdatedMixin, models.Model):
    name = models.CharField(max_length=150)
    display_name = models.CharField(max_length=150)
    link_to_award = models.BooleanField("Should link to an Award?")
    award_role_limit = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    link_to_membership = models.BooleanField("Should link to a Membership?")
    additional_url = models.BooleanField("Should allow for additional URL?")
    generic_relation_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    generic_relation_multiple_items = models.BooleanField(
        "Should generic relation point to more than 1 items?",
    )

    def __str__(self) -> str:
        return self.display_name


class CommunityRoleInactivation(CreatedUpdatedMixin, models.Model):
    name = models.CharField(max_length=150)

    def __str__(self) -> str:
        return self.name


class CommunityRole(CreatedUpdatedMixin, models.Model):
    config = models.ForeignKey(CommunityRoleConfig, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    award = models.ForeignKey(Award, on_delete=models.PROTECT, null=True, blank=True)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    inactivation = models.ForeignKey(
        CommunityRoleInactivation, on_delete=models.PROTECT, null=True, blank=True
    )
    membership = models.ForeignKey(
        Membership, on_delete=models.PROTECT, null=True, blank=True
    )
    url = models.URLField("URL", blank=True, default="")

    # Django doesn't support Generic Relation M2M, so to circumvent this issue
    # there's a generic relation Content Type field
    # `CommunityRoleConfig.generic_relation_content_type` and here in the array field
    # are kept indices for related objects in this content type model.
    generic_relation_m2m = ArrayField(
        models.PositiveIntegerField(), default=list, blank=True
    )

    def __str__(self) -> str:
        return f'Community Role "{self.config}" for {self.person}'

    def get_absolute_url(self):
        return reverse("communityrole_details", kwargs={"pk": self.pk})
