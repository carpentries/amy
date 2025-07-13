import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.urls import reverse

from workshops.consts import STR_LONG, STR_LONGEST
from workshops.mixins import ActiveMixin, CreatedUpdatedMixin
from workshops.models import Curriculum, Membership, Person


class EventCategory(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """Describe category of event or account benefit. Part of Service Offering Model 2025."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=STR_LONG)
    description = models.CharField(max_length=STR_LONGEST)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("event-category-details", kwargs={"pk": self.pk})


class Account(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """The individual or organisation that purchases benefits."""

    ACCOUNT_TYPE_CHOICES = (
        ("individual", "individual"),
        ("organisation", "organisation"),
        ("consortium", "consortium"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_type = models.CharField(max_length=30, choices=ACCOUNT_TYPE_CHOICES)

    generic_relation_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=(
            Q(app_label="workshops", model="person")
            | Q(app_label="workshops", model="organization")
            | Q(app_label="fiscal", model="consortium")
        ),
    )
    generic_relation_pk = models.PositiveBigIntegerField()
    generic_relation = GenericForeignKey("generic_relation_content_type", "generic_relation_pk")

    class Meta:
        constraints = [
            # One account matches one generic relation object (defined by the pair above)
            models.UniqueConstraint(
                fields=["generic_relation_content_type", "generic_relation_pk"],
                name="unique_account_relation",
            )
        ]


class AccountOwner(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """Person appointed as account owner. Mostly for organisations."""

    PERMISSION_TYPE_CHOICES = (
        ("account_contact", "account_contact"),
        ("billing_contact", "billing_contact"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    permission_type = models.CharField(max_length=30, choices=PERMISSION_TYPE_CHOICES)


class Benefit(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """A single good purchased for an account."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    event_category = models.ForeignKey(EventCategory, on_delete=models.PROTECT)

    # null if event category is a'la carte or open training
    membership = models.ForeignKey(Membership, on_delete=models.PROTECT, null=True)

    # null if event category is workshop, defined if skillup
    curriculum = models.ForeignKey(Curriculum, on_delete=models.PROTECT, null=True)

    start_date = models.DateField()
    end_date = models.DateField()
    allocation = models.PositiveIntegerField()
