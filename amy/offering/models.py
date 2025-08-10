from datetime import date
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from fiscal.models import Partnership
from workshops.consts import STR_LONG, STR_LONGEST
from workshops.mixins import ActiveMixin, CreatedUpdatedMixin
from workshops.models import Curriculum, Person
from workshops.utils.dates import human_daterange


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
            | Q(app_label="fiscal", model="partnership")
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

    def __str__(self) -> str:
        return f'Account {self.account_type} for "{self.generic_relation}"'

    def get_absolute_url(self) -> str:
        return reverse("account-details", kwargs={"pk": self.pk})


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
    """A single good available to be purchased for an account."""

    UNIT_TYPE_CHOICES = (
        ("seat", "seat"),
        ("event", "event"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=STR_LONG)
    description = models.CharField(max_length=STR_LONGEST)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPE_CHOICES)

    def __str__(self) -> str:
        return f'Benefit "{self.name}" ({self.unit_type})'

    def get_absolute_url(self) -> str:
        return reverse("benefit-details", kwargs={"pk": self.pk})


class AccountBenefit(CreatedUpdatedMixin, models.Model):
    """A single benefit purchased for an account."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    partnership = models.ForeignKey(Partnership, on_delete=models.PROTECT, null=True, blank=True)
    benefit = models.ForeignKey(Benefit, on_delete=models.PROTECT)

    # null if event category is workshop, defined if skillup
    curriculum = models.ForeignKey(Curriculum, on_delete=models.PROTECT, null=True, blank=True)

    start_date = models.DateField()
    end_date = models.DateField()
    allocation = models.PositiveIntegerField()

    @property
    def human_daterange(self) -> str:
        return human_daterange(self.start_date, self.end_date)

    def active(self, current_date: date | None = None) -> bool:
        return self.start_date <= (current_date or timezone.now().date()) <= self.end_date

    def __str__(self) -> str:
        return (
            f'{self.benefit} for "{self.partnership or self.account.generic_relation}" '
            f"(allocation: {self.allocation}, valid: {self.human_daterange})"
        )

    def get_absolute_url(self) -> str:
        return reverse("account-benefit-details", kwargs={"pk": self.pk})
