from django.db import models
from django.urls import reverse
from reversion import revisions as reversion

from workshops.mixins import CreatedUpdatedMixin, StateMixin
from workshops.models import Event, Person


@reversion.register
class InstructorRecruitment(CreatedUpdatedMixin, models.Model):
    """Instructor recruitment process for a given event."""

    STATUS_CHOICES = (
        ("o", "Open"),
        ("c", "Closed"),
    )
    status = models.CharField(
        max_length=1, choices=STATUS_CHOICES, null=False, blank=False, default="o"
    )
    notes = models.TextField(default="", null=False, blank=True)
    event = models.OneToOneField(
        Event, on_delete=models.PROTECT, null=False, blank=False
    )

    def get_absolute_url(self):
        return reverse("instructorrecruitment_details", kwargs={"pk": self.pk})

    def __str__(self):
        return (
            f"Instructor Recruitment Process ({self.get_status_display()}) for "
            f"event {self.event.slug}"
        )


@reversion.register
class InstructorRecruitmentSignup(CreatedUpdatedMixin, StateMixin, models.Model):
    """Instructor signup for a given event instructor recruitment process."""

    recruitment = models.ForeignKey(
        InstructorRecruitment, on_delete=models.CASCADE, null=False, blank=False
    )
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, null=False, blank=False
    )

    INTEREST_CHOICES = (
        ("session", "Whole session"),
        ("part", "Part of session"),
        ("support", "Supporting instructor"),
    )
    interest = models.CharField(
        max_length=10, choices=INTEREST_CHOICES, null=False, blank=False
    )
    user_notes = models.TextField(default="", null=False, blank=True)
    notes = models.TextField(default="", null=False, blank=True)  # admin notes
