from django.db import models


class RQJobsMixin(models.Model):
    rq_jobs = models.ManyToManyField(
        "autoemails.RQJob",
        verbose_name="Related Redis Queue jobs",
        help_text="This should be filled out by AMY itself.",
        blank=True,
    )

    class Meta:
        abstract = True
