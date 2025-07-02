import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from workshops.models import Curriculum, EventCategory, Membership, Person


class Account(models.Model):
    """The individual or organisation that purchases benefits."""

    ACCOUNT_TYPE_CHOICES = (
        ("individual", "individual"),
        ("organisation", "organisation"),
        ("consortium", "consortium"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)

    generic_relation_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=(Q(app_label="workshops", model="person") | Q(app_label="workshops", model="organization")),
    )
    generic_relation_pk = models.PositiveBigIntegerField()
    generic_relation = GenericForeignKey("generic_relation_content_type", "generic_relation_pk")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["generic_relation_content_type", "generic_relation_pk"],
                name="unique_account_relation",
            )
        ]


class AccountOwner(models.Model):
    """Person appointed as account owner. Mostly for organisations."""

    PERMISSION_TYPE_CHOICES = (
        ("account_contact", "account_contact"),
        ("billing_contact", "billing_contact"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    permission_type = models.CharField(max_length=20, choices=PERMISSION_TYPE_CHOICES)


class Benefit(models.Model):
    """A single good purchased for an account."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    event_category = models.ForeignKey(EventCategory, on_delete=models.PROTECT)

    # null if a'la carte or open training
    membership = models.ForeignKey(Membership, on_delete=models.PROTECT, null=True)

    # null if workshop, defined if skillup
    curriculum = models.ForeignKey(Curriculum, on_delete=models.PROTECT, null=True)

    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    allocation = models.PositiveIntegerField()
