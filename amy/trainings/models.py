from django.db import models
from django.db.models import Case, When
from reversion import revisions as reversion

from workshops.consts import STR_LONG, STR_MED
from workshops.mixins import CreatedUpdatedArchivedMixin


class InvolvementManager(models.Manager):
    def default_order(
        self,
    ):
        """A specific order_by() clause with semi-ninja code."""

        # Always have 'Other' option at the end of the list, don't worry about the rest
        qs = self.order_by(
            Case(
                When(name="Other", then=10),
                default=1,
            ),
            "name",
        )

        return qs


@reversion.register
class Involvement(CreatedUpdatedArchivedMixin, models.Model):
    display_name = models.CharField(
        max_length=STR_LONG, help_text="This name will appear on community facing pages"
    )
    name = models.CharField(
        max_length=STR_MED,
        help_text="A short descriptive name for internal use",
        unique=True,
    )

    # Determines whether TrainingProgress.url is required (True) or must be
    # null (False).
    url_required = models.BooleanField(default=False)

    # Determines whether TrainingProgress.date is required (True) or must be
    # null (False).
    date_required = models.BooleanField(default=True)

    # Determines whether TrainingProgress.trainee_notes is required (True) or must be
    # null (False).
    notes_required = models.BooleanField(default=False)

    objects = InvolvementManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.display_name
