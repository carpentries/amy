from datetime import date, timedelta

from django.db import models
from django.urls import reverse
from reversion import revisions as reversion

from autoemails.mixins import RQJobsMixin
from workshops.mixins import AssignmentMixin, CreatedUpdatedMixin, StateMixin
from workshops.models import Event, Person


@reversion.register
class InstructorRecruitment(CreatedUpdatedMixin, AssignmentMixin, models.Model):
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

    class Priority(models.IntegerChoices):
        LOW = 1
        MEDIUM = 2
        HIGH = 3

    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.LOW,
    )

    def get_absolute_url(self):
        return reverse("instructorrecruitment_details", kwargs={"pk": self.pk})

    def __str__(self):
        return (
            f"Instructor Recruitment Process ({self.get_status_display()}) for "
            f"event {self.event.slug}"
        )

    @staticmethod
    def calculate_priority(event: Event) -> Priority:
        online = event.tags.filter(name="online")
        if not event.start:
            return InstructorRecruitment.Priority.LOW

        time_to_start = event.start - date.today()
        inperson_offset = 30 if not online else 0

        if time_to_start >= timedelta(days=60 + inperson_offset):
            return InstructorRecruitment.Priority.LOW
        elif time_to_start > timedelta(days=30 + inperson_offset):
            return InstructorRecruitment.Priority.MEDIUM
        else:
            return InstructorRecruitment.Priority.HIGH


@reversion.register
class InstructorRecruitmentSignup(
    CreatedUpdatedMixin, StateMixin, RQJobsMixin, models.Model
):
    """Instructor signup for a given event instructor recruitment process."""

    recruitment = models.ForeignKey(
        InstructorRecruitment,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="signups",
    )
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, null=False, blank=False
    )

    INTEREST_CHOICES = (
        ("session", "Whole session"),
        ("part", "Part of session"),  # choice disabled, see #2068
        ("support", "Supporting instructor"),  # choice disabled, see #2068
    )
    interest = models.CharField(
        max_length=10,
        choices=INTEREST_CHOICES,
        null=False,
        blank=False,
        default="session",
    )
    user_notes = models.TextField(default="", null=False, blank=True)
    notes = models.TextField(default="", null=False, blank=True)  # admin notes
