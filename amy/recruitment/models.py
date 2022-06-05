from datetime import date, timedelta

from django.db import models
from django.db.models import (
    Case,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Value,
    When,
)
from django.urls import reverse
from reversion import revisions as reversion

from autoemails.mixins import RQJobsMixin
from workshops.mixins import AssignmentMixin, CreatedUpdatedMixin, StateMixin
from workshops.models import Event, Person, Tag


class RecruitmentPriority(models.IntegerChoices):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class InstructorRecruitmentManager(models.Manager):
    def annotate_with_priority(self) -> QuerySet["InstructorRecruitment"]:
        today = date.today()
        cutoff_low_online = today + timedelta(days=60)
        cutoff_medium_online = today + timedelta(days=30)
        cutoff_low_inperson = today + timedelta(days=90)
        cutoff_medium_inperson = today + timedelta(days=60)

        # Online tag existence is checked with a subquery + Exists() to solve issue
        # with event without any tags (wrong results with:
        #   `.annotate(event__tag__name="online")`
        # ).
        online_tag_exists = Tag.objects.filter(event=OuterRef("event"), name="online")

        # If event is online, then it has the following priority:
        # 1) LOW if start >= 60 days
        # 2) MEDIUM if start > 30 days
        # 3) HIGH otherwise.
        # If the event is not online, then:
        # 1) LOW if start >= 90 days
        # 2) MEDIUM if start > 60 days
        # 3) HIGH otherwise.
        q_online = Q(online_tag_exists=True)
        q_low_online = Q(event__start__gte=cutoff_low_online)
        q_medium_online = Q(event__start__gt=cutoff_medium_online)
        q_low_inperson = Q(event__start__gte=cutoff_low_inperson)
        q_medium_inperson = Q(event__start__gt=cutoff_medium_inperson)
        q_low = (q_online & q_low_online) | (~q_online & q_low_inperson)
        q_medium = (q_online & q_medium_online) | (~q_online & q_medium_inperson)

        return self.annotate(
            online_tag_exists=Exists(online_tag_exists),
            automatic_priority=Case(
                When(q_low, then=Value(RecruitmentPriority.LOW.value)),
                When(q_medium, then=Value(RecruitmentPriority.MEDIUM.value)),
                default=Value(RecruitmentPriority.HIGH.value),
                output_field=IntegerField(),
            ),
            calculated_priority=Case(
                When(priority__isnull=False, then=F("priority")),
                default=F("automatic_priority"),
                output_field=IntegerField(),
            ),
        )


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

    objects = InstructorRecruitmentManager()

    priority = models.IntegerField(
        choices=RecruitmentPriority.choices,
        help_text="If no priority is selected, automated priority will be calculated "
        "based on the days to start of the event.",
        null=True,
        blank=True,
    )

    def get_absolute_url(self):
        return reverse("instructorrecruitment_details", kwargs={"pk": self.pk})

    def __str__(self):
        return (
            f"Instructor Recruitment Process ({self.get_status_display()}) for "
            f"event {self.event.slug}"
        )

    @staticmethod
    def calculate_priority(event: Event) -> RecruitmentPriority:
        online = event.tags.filter(name="online")
        if not event.start:
            return RecruitmentPriority.LOW

        time_to_start = event.start - date.today()
        inperson_offset = 30 if not online else 0

        if time_to_start >= timedelta(days=60 + inperson_offset):
            return RecruitmentPriority.LOW
        elif time_to_start > timedelta(days=30 + inperson_offset):
            return RecruitmentPriority.MEDIUM
        else:
            return RecruitmentPriority.HIGH


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
