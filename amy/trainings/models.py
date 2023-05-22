from django.db import models
from reversion import revisions as reversion

from workshops.consts import STR_LONG, STR_MED
from workshops.mixins import CreatedUpdatedArchivedMixin

# ------------------------------------------------------------


@reversion.register
class Involvement(CreatedUpdatedArchivedMixin, models.Model):
    display_name = models.CharField(max_length=STR_LONG)
    name = models.CharField(max_length=STR_MED)

    # Determines whether TrainingProgress.url is required (True) or must be
    # null (False).
    url_required = models.BooleanField(default=False)

    # Determines whether TrainingProgress.curriculum is required (True) or must be
    # null (False).
    curriculum_required = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.display_name
