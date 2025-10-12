import datetime
import re
from typing import Annotated, Any, Collection, TypedDict, cast
from urllib.parse import quote
import uuid

import airportsdata
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import (
    Case,
    Count,
    F,
    IntegerField,
    Manager,
    PositiveIntegerField,
    Q,
    QuerySet,
    Sum,
    When,
)
from django.db.models.aggregates import Aggregate
from django.db.models.functions import Coalesce, Greatest
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import format_lazy
from django_countries.fields import CountryField
from django_stubs_ext import Annotations
from reversion import revisions as reversion
from reversion.models import Version
from social_django.models import UserSocialAuth

from trainings.models import Involvement
from workshops import github_auth
from workshops.consts import (
    FEE_DETAILS_URL,
    STR_LONG,
    STR_LONGEST,
    STR_MED,
    STR_REG_KEY,
    STR_SHORT,
)
from workshops.fields import NullableGithubUsernameField, choice_field_with_other
from workshops.mixins import (
    ActiveMixin,
    AssignmentMixin,
    COCAgreementMixin,
    CreatedUpdatedArchivedMixin,
    CreatedUpdatedMixin,
    DataPrivacyAgreementMixin,
    EventLinkMixin,
    GenderMixin,
    HostResponsibilitiesMixin,
    InstructorAvailabilityMixin,
    SecondaryEmailMixin,
    StateExtendedMixin,
    StateMixin,
)
from workshops.signals import person_archived_signal
from workshops.utils.dates import human_daterange
from workshops.utils.emails import find_emails
from workshops.utils.reports import reports_link

IATA_AIRPORTS = airportsdata.load("IATA")

# ------------------------------------------------------------


class OrganizationManager(models.Manager["Organization"]):
    ADMIN_DOMAINS = [
        "self-organized",
        "software-carpentry.org",
        "datacarpentry.org",
        "librarycarpentry.org",
        # Instructor Training organisation
        "carpentries.org",
        # Collaborative Lesson Development Training organisation
        "carpentries.org/community-lessons/",
    ]

    def administrators(self) -> QuerySet["Organization"]:
        return self.get_queryset().filter(domain__in=self.ADMIN_DOMAINS)


@reversion.register
class Organization(models.Model):
    """Represent an organization, academic or business."""

    domain = models.CharField(max_length=STR_LONG, unique=True)
    fullname = models.CharField(max_length=STR_LONG, unique=True)
    country = CountryField(null=True, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    affiliated_organizations = models.ManyToManyField["Organization", Any]("Organization", blank=True, symmetrical=True)

    objects = OrganizationManager()

    def __str__(self) -> str:
        return "{} <{}>".format(self.fullname, self.domain)

    @property
    def domain_quoted(self) -> str:
        return quote(self.domain, safe="")

    def get_absolute_url(self) -> str:
        return reverse("organization_details", args=[self.domain_quoted])

    class Meta:
        ordering = ("domain",)


class MemberRole(models.Model):
    name = models.CharField(max_length=STR_MED)
    verbose_name = models.CharField(max_length=STR_LONG, blank=True, default="")

    def __str__(self) -> str:
        return self.verbose_name if self.verbose_name else self.name


class Member(models.Model):
    membership = models.ForeignKey("Membership", on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    role = models.ForeignKey(MemberRole, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "organization", "role"],
                name="unique_member_role_in_membership",
            )
        ]


class MembershipSeatUsage(TypedDict):
    instructor_training_seats_total: int
    instructor_training_seats_utilized: int
    instructor_training_seats_remaining: int


class MembershipManager(models.Manager["Membership"]):
    def annotate_with_seat_usage(self) -> QuerySet[Annotated["Membership", Annotations[MembershipSeatUsage]]]:
        return self.get_queryset().annotate(
            instructor_training_seats_total=(
                # Public
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # Coalesce returns first non-NULL value
                + Coalesce("public_instructor_training_seats_rolled_from_previous", 0)
                # Inhouse
                + F("inhouse_instructor_training_seats")
                + F("additional_inhouse_instructor_training_seats")
                + Coalesce("inhouse_instructor_training_seats_rolled_from_previous", 0)
            ),
            instructor_training_seats_utilized=(Count("task", filter=Q(task__role__name="learner"))),
            instructor_training_seats_remaining=(
                # Public
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # Coalesce returns first non-NULL value
                + Coalesce("public_instructor_training_seats_rolled_from_previous", 0)
                - Count("task", filter=Q(task__role__name="learner", task__seat_public=True))
                - Coalesce("public_instructor_training_seats_rolled_over", 0)
                # Inhouse
                + F("inhouse_instructor_training_seats")
                + F("additional_inhouse_instructor_training_seats")
                + Coalesce("inhouse_instructor_training_seats_rolled_from_previous", 0)
                - Count(
                    "task",
                    filter=Q(task__role__name="learner", task__seat_public=False),
                )
                - Coalesce("inhouse_instructor_training_seats_rolled_over", 0)
            ),
        )


@reversion.register
class Membership(models.Model):
    """Represent a details of Organization's membership."""

    name = models.CharField(max_length=STR_LONG)
    MEMBERSHIP_CHOICES = (
        ("partner", "Partner"),
        ("affiliate", "Affiliate"),
        ("sponsor", "Sponsor"),
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
        ("platinum", "Platinum"),
        ("titanium", "Titanium"),
        ("alacarte", "A la carte"),
    )
    variant = models.CharField(
        max_length=STR_MED,
        null=False,
        blank=False,
        choices=MEMBERSHIP_CHOICES,
    )
    agreement_start = models.DateField()
    agreement_end = models.DateField(
        help_text="If an extension is being granted, do not manually edit the end date."
        ' Use the "Extend" button on membership details page instead.'
    )
    extensions = ArrayField(
        models.PositiveIntegerField(),
        help_text="Number of days the agreement was extended. The field stores "
        "multiple extensions. The agreement end date has been moved by a cumulative "
        "number of days from this field.",
        default=list,
    )
    CONTRIBUTION_CHOICES = (
        ("financial", "Financial"),
        ("person-days", "Person-days"),
        ("other", "Other"),
    )
    contribution_type = models.CharField(
        max_length=STR_MED,
        null=False,
        blank=False,
        choices=CONTRIBUTION_CHOICES,
    )
    workshops_without_admin_fee_per_agreement = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Acceptable number of workshops without admin fee per agreement duration",
    )
    workshops_without_admin_fee_rolled_from_previous = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Workshops without admin fee rolled over from previous membership.",
    )
    workshops_without_admin_fee_rolled_over = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Workshops without admin fee rolled over into next membership.",
    )
    # according to Django docs, PositiveIntegerFields accept 0 as valid as well
    public_instructor_training_seats = models.PositiveIntegerField(
        null=False,
        blank=False,
        default=0,
        verbose_name="Public instructor training seats",
        help_text="Number of public seats in instructor trainings",
    )
    additional_public_instructor_training_seats = models.PositiveIntegerField(
        null=False,
        blank=False,
        default=0,
        verbose_name="Additional public instructor training seats",
        help_text="Use this field if you want to grant more public seats than the agreement provides for.",
    )
    public_instructor_training_seats_rolled_from_previous = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Public instructor training seats rolled over from previous membership.",
    )
    public_instructor_training_seats_rolled_over = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Public instructor training seats rolled over into next membership.",
    )
    inhouse_instructor_training_seats = models.PositiveIntegerField(
        null=False,
        blank=False,
        default=0,
        verbose_name="In-house instructor training seats",
        help_text="Number of in-house seats in instructor trainings",
    )
    additional_inhouse_instructor_training_seats = models.PositiveIntegerField(
        null=False,
        blank=False,
        default=0,
        verbose_name="Additional in-house instructor training seats",
        help_text="Use this field if you want to grant more in-house seats than the agreement provides for.",
    )
    inhouse_instructor_training_seats_rolled_from_previous = models.PositiveIntegerField(  # noqa
        null=True,
        blank=True,
        help_text="In-house instructor training seats rolled over from previous membership.",  # noqa
    )
    inhouse_instructor_training_seats_rolled_over = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="In-house instructor training seats rolled over into next membership.",  # noqa
    )
    organizations = models.ManyToManyField(
        Organization,
        blank=False,
        related_name="memberships",
        through=Member,
    )

    registration_code = models.CharField(
        max_length=STR_MED,
        null=True,
        blank=True,
        unique=True,
        verbose_name="Registration Code",
        help_text="Unique registration code used for Eventbrite and trainee application.",
    )

    agreement_link = models.URLField(
        blank=False,
        default="",
        verbose_name="Link to member agreement",
        help_text="Link to member agreement document or folder in Google Drive",
    )

    PUBLIC_STATUS_CHOICES = (
        ("public", "Public"),
        ("private", "Private"),
    )
    public_status = models.CharField(
        max_length=20,
        choices=PUBLIC_STATUS_CHOICES,
        default=PUBLIC_STATUS_CHOICES[1][0],
        verbose_name="Can this membership be publicized on The carpentries websites?",
        help_text="Public memberships may be listed on any of The Carpentries websites.",
    )

    emergency_contact = models.TextField(blank=True)

    consortium = models.BooleanField(
        default=False,
        help_text="Determines whether this is a group of organisations working together under a consortium.",
    )

    persons = models.ManyToManyField["Person", Any](
        "Person",
        blank=True,
        related_name="memberships",
        through="fiscal.MembershipTask",
    )

    rolled_to_membership = models.OneToOneField(
        "Membership",
        on_delete=models.SET_NULL,
        related_name="rolled_from_membership",
        null=True,
    )

    objects = MembershipManager()

    def __str__(self) -> str:
        dates = human_daterange(self.agreement_start, self.agreement_end)
        variant = self.variant.title()

        if self.consortium:
            return f"{self.name} {variant} membership {dates} (consortium)"
        else:
            return f"{self.name} {variant} membership {dates}"

    def get_absolute_url(self) -> str:
        return reverse("membership_details", args=[self.id])

    def active_on_date(self, date: datetime.date, grace_before: int = 0, grace_after: int = 0) -> bool:
        """Returns True if the date is within the membership agreement dates,
        with an optional grace period (in days) at the start and/or end of the
        agreement.
        """
        start_date = self.agreement_start - datetime.timedelta(days=grace_before)
        end_date = self.agreement_end + datetime.timedelta(days=grace_after)
        return start_date <= date <= end_date

    def _base_queryset(self) -> QuerySet["Event"]:
        """Provide universal queryset for looking up workshops for this membership."""
        cancelled = Q(tags__name="cancelled") | Q(tags__name="stalled")
        return Event.objects.filter(membership=self).exclude(cancelled).distinct()

    def _workshops_without_admin_fee_queryset(self) -> QuerySet["Event"]:
        """Provide universal queryset for looking up centrally-organised workshops for
        this membership."""
        return (
            self._base_queryset()
            .filter(administrator__in=Organization.objects.administrators())
            .exclude(administrator__domain="self-organized")
        )

    def _workshops_without_admin_fee_completed_queryset(self) -> QuerySet["Event"]:
        return self._workshops_without_admin_fee_queryset().filter(start__lt=datetime.date.today())

    def _workshops_without_admin_fee_planned_queryset(self) -> QuerySet["Event"]:
        return self._workshops_without_admin_fee_queryset().filter(start__gte=datetime.date.today())

    @property
    def workshops_without_admin_fee_total_allowed(self) -> int:
        """Available for counting, "contracted" centrally-organised workshops.

        This number represents the real number of available workshops for counting
        completed / planned / remaining no-fee workshops.

        Because the data may be entered incorrectly, a sharp cutoff at 0 was introduced,
        meaning this value won't be ever negative."""
        a = self.workshops_without_admin_fee_per_agreement or 0
        b = self.workshops_without_admin_fee_rolled_from_previous or 0
        return a + b

    @property
    def workshops_without_admin_fee_available(self) -> int:
        """Available for counting, "contracted" centrally-organised workshops.

        This number represents the real number of available workshops for counting
        completed / planned / remaining no-fee workshops.

        Because the data may be entered incorrectly, a sharp cutoff at 0 was introduced,
        meaning this value won't be ever negative."""
        a = self.workshops_without_admin_fee_total_allowed
        b = self.workshops_without_admin_fee_rolled_over or 0
        return max(a - b, 0)

    @cached_property
    def workshops_without_admin_fee_completed(self) -> int:
        """Count centrally-organised workshops already hosted by this membership.

        This value must not be higher than "contracted" (or available for counting)
        no-fee workshops.

        Excess is counted towards discounted-fee completed workshops."""
        return min(
            self._workshops_without_admin_fee_completed_queryset().count(),
            self.workshops_without_admin_fee_available,
        )

    @cached_property
    def workshops_without_admin_fee_planned(self) -> int:
        """Count centrally-organised workshops hosted in future by this membership.

        This value must not be higher than "contracted" (or available for counting)
        no-fee workshops reduced by already completed no-fee workshops.

        Excess is counted towards discounted-fee planned workshops."""
        return min(
            self._workshops_without_admin_fee_planned_queryset().count(),
            self.workshops_without_admin_fee_available - self.workshops_without_admin_fee_completed,
        )

    @property
    def workshops_without_admin_fee_remaining(self) -> int:
        """Count remaining centrally-organised workshops for the agreement."""
        a = self.workshops_without_admin_fee_available
        b = self.workshops_without_admin_fee_completed
        c = self.workshops_without_admin_fee_planned

        # can't get below 0, that's when discounted workshops kick in
        return max(a - b - c, 0)

    @cached_property
    def workshops_discounted_completed(self) -> int:
        """Any centrally-organised workshops exceeding the workshops without fee allowed
        number - already completed."""
        return max(
            self._workshops_without_admin_fee_completed_queryset().count() - self.workshops_without_admin_fee_available,
            0,
        )

    @cached_property
    def workshops_discounted_planned(self) -> int:
        """Any centrally-organised workshops exceeding the workshops without fee allowed
        number - to happen in future."""
        return max(
            self._workshops_without_admin_fee_planned_queryset().count() - self.workshops_without_admin_fee_available,
            0,
        )

    def _self_organized_workshops_queryset(self) -> QuerySet["Event"]:
        """Provide universal queryset for looking up self-organised events for this
        membership."""
        self_organized = Q(administrator=None) | Q(administrator__domain="self-organized")
        return self._base_queryset().filter(self_organized)

    @cached_property
    def self_organized_workshops_completed(self) -> int:
        """Count self-organized workshops hosted the year agreement started (completed,
        ie. in past)."""
        return self._self_organized_workshops_queryset().filter(start__lt=datetime.date.today()).count()

    @cached_property
    def self_organized_workshops_planned(self) -> int:
        """Count self-organized workshops hosted the year agreement started (planned,
        ie. in future)."""
        return self._self_organized_workshops_queryset().filter(start__gte=datetime.date.today()).count()

    @property
    def public_instructor_training_seats_total(self) -> int:
        """Calculate combined public instructor training seats total.

        Unlike workshops w/o admin fee, instructor training seats have two numbers
        combined to calculate total of allowed instructor training seats in ITT events.
        """
        a = self.public_instructor_training_seats
        b = self.additional_public_instructor_training_seats
        c = self.public_instructor_training_seats_rolled_from_previous or 0
        return a + b + c

    @cached_property
    def public_instructor_training_seats_utilized(self) -> int:
        """Count number of learner tasks that point to this membership."""
        return self.task_set.filter(role__name="learner", seat_public=True).count()

    @property
    def public_instructor_training_seats_remaining(self) -> int:
        """Count remaining public seats for instructor training."""
        a = self.public_instructor_training_seats_total
        b = self.public_instructor_training_seats_utilized
        c = self.public_instructor_training_seats_rolled_over or 0
        return a - b - c

    @property
    def inhouse_instructor_training_seats_total(self) -> int:
        """Calculate combined in-house instructor training seats total.

        Unlike workshops w/o admin fee, instructor training seats have two numbers
        combined to calculate total of allowed instructor training seats in ITT events.
        """
        a = self.inhouse_instructor_training_seats
        b = self.additional_inhouse_instructor_training_seats
        c = self.inhouse_instructor_training_seats_rolled_from_previous or 0
        return a + b + c

    @cached_property
    def inhouse_instructor_training_seats_utilized(self) -> int:
        """Count number of learner tasks that point to this membership."""
        return self.task_set.filter(role__name="learner", seat_public=False).count()

    @property
    def inhouse_instructor_training_seats_remaining(self) -> int:
        """Count remaining in-house seats for instructor training."""
        a = self.inhouse_instructor_training_seats_total
        b = self.inhouse_instructor_training_seats_utilized
        c = self.inhouse_instructor_training_seats_rolled_over or 0
        return a - b - c


# ------------------------------------------------------------


@reversion.register
class Airport(models.Model):
    """Represent an airport (used to locate instructors)."""

    iata = models.CharField(
        max_length=STR_SHORT,
        unique=True,
        verbose_name="IATA code",
        help_text='<a href="https://www.world-airport-codes.com/">Look up code</a>',
    )
    fullname = models.CharField(max_length=STR_LONG, unique=True, verbose_name="Airport name")
    country = CountryField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self) -> str:
        return "{0}: {1}".format(self.iata, self.fullname)

    def get_absolute_url(self) -> str:
        return reverse("airport_details", args=[str(self.iata)])

    class Meta:
        ordering = ("iata",)


# ------------------------------------------------------------


class PersonInstructorEligibility(TypedDict):
    passed_training: int
    passed_get_involved: int
    passed_welcome: int
    passed_demo: int
    instructor_eligible: int


class PersonManager(BaseUserManager["Person"]):
    """
    Create users and superusers from command line.

    For example:

      $ python manage.py createsuperuser
    """

    def create_user(
        self, username: str, personal: str, family: str, email: str, password: str | None = None
    ) -> "Person":
        """
        Create and save a normal (not-super) user.
        """
        user = self.model(
            username=username,
            personal=personal,
            family=family,
            email=self.normalize_email(email),
            is_superuser=False,
            is_active=True,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, personal: str, family: str, email: str, password: str) -> "Person":
        """
        Create and save a superuser.
        """
        user = self.model(
            username=username,
            personal=personal,
            family=family,
            email=self.normalize_email(email),
            is_superuser=True,
            is_active=True,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username: str | None) -> "Person":
        """Let's make this command so that it gets user by *either* username or
        email.  Original behavior is to get user by USERNAME_FIELD."""
        if isinstance(username, str) and "@" in username:
            return self.get(email=username)
        else:
            return super().get_by_natural_key(username)

    def annotate_with_instructor_eligibility(
        self,
    ) -> QuerySet[Annotated["Person", Annotations[PersonInstructorEligibility]]]:
        def passed(requirement: str) -> Aggregate:
            return Sum(
                Case(
                    When(
                        trainingprogress__requirement__name=requirement,
                        trainingprogress__state="p",
                        then=1,
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            )

        def passed_either(*reqs: str) -> Aggregate:
            return Sum(
                Case(
                    *[
                        When(
                            trainingprogress__requirement__name=req,
                            trainingprogress__state="p",
                            then=1,
                        )
                        for req in reqs
                    ],
                    default=0,
                    output_field=IntegerField(),
                )
            )

        return self.annotate(
            passed_training=passed("Training"),
            passed_get_involved=passed("Get Involved"),
            passed_welcome=passed("Welcome Session"),
            passed_demo=passed("Demo"),
        ).annotate(
            # We're using Maths to calculate "binary" score for a person to
            # be instructor badge eligible. Legend:
            # * means "AND"
            # + means "OR"
            instructor_eligible=(
                F("passed_training") * F("passed_welcome") * F("passed_get_involved") * F("passed_demo")
            )
        )

    def annotate_with_role_count(self) -> QuerySet["Person"]:
        return self.annotate(
            num_instructor=Count(
                "task",
                filter=(Q(task__role__name="instructor") & ~Q(task__event__administrator__domain="carpentries.org")),
                distinct=True,
            ),
            num_trainer=Count(
                "task",
                filter=(Q(task__role__name="instructor") & Q(task__event__administrator__domain="carpentries.org")),
                distinct=True,
            ),
            num_helper=Count("task", filter=Q(task__role__name="helper"), distinct=True),
            num_learner=Count("task", filter=Q(task__role__name="learner"), distinct=True),
            num_supporting=Count(
                "task",
                filter=Q(task__role__name="supporting-instructor"),
                distinct=True,
            ),
            num_organizer=Count("task", filter=Q(task__role__name="organizer"), distinct=True),
        )

    def duplication_review_expired(self) -> QuerySet["Person"]:
        return self.filter(
            Q(duplication_reviewed_on__isnull=True)
            | Q(last_updated_at__gte=F("duplication_reviewed_on") + datetime.timedelta(minutes=1))
        )


@reversion.register
class Person(
    AbstractBaseUser,
    PermissionsMixin,
    CreatedUpdatedArchivedMixin,
    GenderMixin,
    SecondaryEmailMixin,
):
    """Represent a single person."""

    # These attributes should always contain field names of Person
    PERSON_UPLOAD_FIELDS = ("personal", "family", "email")
    PERSON_TASK_EXTRA_FIELDS = ("event", "role")
    PERSON_TASK_UPLOAD_FIELDS = PERSON_UPLOAD_FIELDS + PERSON_TASK_EXTRA_FIELDS

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = [
        "personal",
        "family",
        "email",
    ]

    personal = models.CharField(
        max_length=STR_LONG,
        verbose_name="Personal (first) name",
    )
    middle = models.CharField(
        max_length=STR_LONG,
        blank=True,
        default="",
        verbose_name="Middle name",
    )
    family = models.CharField(
        max_length=STR_LONG,
        blank=True,
        default="",
        verbose_name="Family (last) name",
    )
    email = models.CharField(  # emailfield?
        max_length=STR_LONG,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Email address",
        help_text="Primary email address, used for communication and as a login.",
    )
    airport_iata = models.CharField(
        null=False,
        blank=False,
        default="",
        help_text="Nearest major airport (IATA code: https://www.world-airport-codes.com/)",
    )
    country = CountryField(
        null=False,
        blank=True,
        default="",
        help_text="Override country of the airport.",
    )
    timezone = models.CharField(
        null=False,
        blank=True,
        default="",
        help_text="Override timezone of the airport.",
    )
    github = NullableGithubUsernameField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="GitHub username",
        help_text="Please put only a single username here.",
    )
    twitter = models.CharField(
        max_length=STR_LONG,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Twitter username",
    )
    bluesky = models.CharField(
        max_length=STR_LONG,
        unique=True,
        null=True,
        blank=True,
        verbose_name="BlueSky username",
    )

    mastodon = models.URLField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="Mastodon URL",
    )

    url = models.CharField(
        max_length=STR_LONG,
        blank=True,
        verbose_name="Personal website",
    )
    username = models.CharField(
        max_length=STR_LONG,
        unique=True,
        validators=[RegexValidator(r"^[\w\-_]+$", flags=re.A)],
    )
    user_notes = models.TextField(
        default="",
        blank=True,
        verbose_name="Notes provided by the user in update profile form.",
    )
    affiliation = models.CharField(
        max_length=STR_LONG,
        default="",
        blank=True,
        help_text="What university, company, lab, or other organization are you affiliated with (if any)?",
    )

    badges = models.ManyToManyField["Badge", "Award"]("Badge", through="Award", through_fields=("person", "badge"))
    lessons = models.ManyToManyField["Lesson", "Qualification"](
        "Lesson",
        through="Qualification",
        verbose_name="Topic and lessons you're comfortable teaching",
        help_text="Please check all that apply.",
        blank=True,
    )
    domains = models.ManyToManyField["KnowledgeDomain", Any](
        "KnowledgeDomain",
        limit_choices_to=~Q(name__startswith="Don't know yet"),
        verbose_name="Areas of expertise",
        help_text="Please check all that apply.",
        blank=True,
    )
    languages = models.ManyToManyField["Language", Any](
        "Language",
        blank=True,
    )

    # new people will be inactive by default
    is_active = models.BooleanField(default=False)

    occupation = models.CharField(
        max_length=STR_LONG,
        verbose_name="Current occupation/career stage",
        blank=True,
        default="",
    )
    orcid = models.CharField(
        max_length=STR_LONG,
        verbose_name="ORCID ID",
        blank=True,
        default="",
    )

    duplication_reviewed_on = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Timestamp of duplication review by admin",
        help_text="Set this to a newer / actual timestamp when Person is reviewed by admin.",
    )

    objects = PersonManager()

    class Meta:
        ordering = ["family", "personal"]

        # additional permissions
        permissions = [
            (
                "can_access_restricted_API",
                "Can this user access the restricted API endpoints?",
            ),
        ]

    @cached_property
    def full_name(self) -> str:
        middle = ""
        if self.middle:
            middle = " {0}".format(self.middle)
        return "{0}{1} {2}".format(self.personal, middle, self.family)

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.personal

    def __str__(self) -> str:
        result = self.full_name
        if self.email:
            result += " <" + self.email + ">"
        return result

    def get_absolute_url(self) -> str:
        return reverse("person_details", args=[str(self.id)])

    @property
    def github_usersocialauth(self) -> QuerySet[UserSocialAuth]:
        """List of all associated GitHub accounts with this Person. Returns
        list of UserSocialAuth."""
        return self.social_auth.filter(provider="github")

    def get_github_uid(self) -> int | None:
        """Return UID (int) of GitHub account for username == `Person.github`.

        Return `None` in case of errors or missing GitHub account.
        May raise ValueError in the case of IO issues."""
        if self.github and self.is_active:
            try:
                # if the username is incorrect, this will throw ValidationError
                github_auth.validate_github_username(self.github)  # type: ignore

                github_uid = github_auth.github_username_to_uid(self.github)  # type: ignore
            except (ValidationError, ValueError):
                github_uid = None
        else:
            github_uid = None

        return github_uid  # type: ignore

    def synchronize_usersocialauth(self) -> UserSocialAuth | bool:
        """Disconnect all GitHub account associated with this Person and
        associates the account with username == `Person.github`, if there is
        such GitHub account.

        May raise GithubException in the case of IO issues."""

        github_uid = self.get_github_uid()

        if github_uid is not None:
            self.github_usersocialauth.delete()
            return cast(
                UserSocialAuth,
                UserSocialAuth.objects.create(provider="github", user=self, uid=github_uid, extra_data={}),
            )
        else:
            return False

    @property
    def is_staff(self) -> bool:
        """Required for logging into admin panel."""
        return self.is_superuser

    @property
    def is_admin(self) -> bool:
        return self._is_admin()

    ADMIN_GROUPS = ("administrators", "steering committee", "invoicing", "trainers")

    def _is_admin(self) -> bool:
        try:
            if self.is_anonymous:
                return False
            else:
                return self.is_superuser or self.groups.filter(name__in=self.ADMIN_GROUPS).exists()
        except AttributeError:
            return False

    def get_missing_instructor_requirements(self) -> list[str]:
        """Returns set of requirements' names (list of strings) that are not
        passed yet by the trainee and are mandatory to become an Instructor.
        """
        fields = [
            ("passed_training", "Training"),
            ("passed_get_involved", "Get Involved"),
            ("passed_welcome", "Welcome Session"),
            ("passed_demo", "Demo"),
        ]
        try:
            return [name for field, name in fields if not getattr(self, field)]
        except AttributeError as e:
            raise Exception("Did you forget to call annotate_with_instructor_eligibility()?") from e

    def get_training_tasks(self) -> QuerySet["Task"]:
        """Returns Tasks related to Instuctor Training events at which this
        person was trained."""
        return Task.objects.filter(person=self, role__name="learner", event__tags__name="TTT")

    def clean(self) -> None:
        """This will be called by the ModelForm.is_valid(). No saving to the
        database."""
        # lowercase the email
        self.email = self.email.lower() if self.email else None

    def clean_airport_iata(self) -> None:
        if not self.airport_iata:
            return None

        try:
            IATA_AIRPORTS[self.airport_iata]
        except KeyError as e:
            raise ValidationError(f"Invalid IATA code: {self.airport_iata}") from e

        return None

    def save(self, *args: Any, **kwargs: Any) -> None:
        # If GitHub username has changed, clear UserSocialAuth table for this
        # person.
        if self.pk is not None:
            orig = Person.objects.get(pk=self.pk)
            github_username_has_changed = orig.github != self.github
            if github_username_has_changed:
                UserSocialAuth.objects.filter(user=self).delete()

        # save empty string as NULL to the database - otherwise there are
        # issues with UNIQUE constraint failing
        self.personal = self.personal.strip()
        if self.family is not None:
            self.family = self.family.strip()
        self.middle = self.middle.strip()
        self.email = self.email.strip() if self.email else None
        self.github = self.github or None
        self.twitter = self.twitter or None
        self.bluesky = self.bluesky or None
        super().save(*args, **kwargs)

    def archive(self) -> None:
        """
        Archives the Person.

        When archiving all personal information associated with the user profile
        should be deleted except for first name, last name and their teaching history.
        """
        # Remove personal information from an archived profile
        self.email = None
        self.country = ""
        self.airport = None
        self.github = None
        self.twitter = None
        self.bluesky = None
        self.mastodon = None
        self.url = ""
        self.user_notes = ""
        self.affiliation = ""
        self.is_active = False
        self.occupation = ""
        self.orcid = ""
        self.secondary_email = ""
        self.gender = GenderMixin.UNDISCLOSED
        self.gender_other = ""
        # Remove permissions
        self.is_superuser = False
        self.groups.clear()
        self.user_permissions.clear()
        self.archived_at = timezone.now()
        # Disconnect all social auth
        self.social_auth.all().delete()
        self.save()

        # This deletes all pre-existing Versions of the object.
        versions = Version.objects.get_for_object(self)
        versions.delete()

        # Send a signal that the profile has been archived. It archives all consents
        # for a person.
        person_archived_signal.send(
            sender=self.__class__,
            person=self,
        )

    @cached_property
    def country_property(self) -> str:
        if self.country:
            return cast(str, self.country)

        try:
            airport = IATA_AIRPORTS[self.airport_iata]
            return airport["country"]
        except KeyError:
            return ""

    @cached_property
    def timezone_property(self) -> str:
        if self.timezone:
            return self.timezone

        try:
            airport = IATA_AIRPORTS[self.airport_iata]
            return airport["tz"]
        except KeyError:
            return ""


# ------------------------------------------------------------


class TagQuerySet(QuerySet["Tag"]):
    CARPENTRIES_TAG_NAMES = ["SWC", "DC", "LC"]
    NON_CARPENTRIES_TAG_NAMES = ["TTT", "Circuits", "CLDT"]
    MAIN_TAG_NAMES = ["SWC", "DC", "LC", "TTT", "ITT", "WiSE"]

    def main_tags(self) -> QuerySet["Tag"]:
        return self.filter(name__in=self.MAIN_TAG_NAMES)

    def carpentries(self) -> QuerySet["Tag"]:
        return self.filter(name__in=self.CARPENTRIES_TAG_NAMES)

    def strings(self) -> list[str]:
        return self.values_list("name", flat=True)  # type: ignore


class Tag(models.Model):
    """Label for grouping events."""

    ITEMS_VISIBLE_IN_SELECT_WIDGET = 19

    name = models.CharField(max_length=STR_MED, unique=True)
    details = models.CharField(max_length=STR_LONG)
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Sorting priority (ascending order). Entries with lower "
        "number will appear first on the list. If entries have the "
        "same number, they're sorted by name.",
    )

    def __str__(self) -> str:
        return self.name

    objects = Manager.from_queryset(TagQuerySet)()

    class Meta:
        ordering = ["priority", "name"]


# ------------------------------------------------------------


class Language(models.Model):
    """A language tag.

    https://tools.ietf.org/html/rfc5646
    """

    name = models.CharField(max_length=STR_LONG, help_text="Description of this language tag in English")
    subtag = models.CharField(
        max_length=STR_SHORT,
        help_text="Primary language subtag.  https://tools.ietf.org/html/rfc5646#section-2.2.1",
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]


# ------------------------------------------------------------


class EventAttendance(TypedDict):
    learner_tasks_count: int
    attendance: int


class EventQuerySet(QuerySet["Event"]):
    """Handles finding past, ongoing and upcoming events"""

    def not_cancelled(self) -> "EventQuerySet":
        """Exclude cancelled events."""
        return self.exclude(tags__name="cancelled")

    def not_unresponsive(self) -> "EventQuerySet":
        """Exclude unresponsive events."""
        return self.exclude(tags__name="unresponsive")

    def active(self) -> "EventQuerySet":
        """Exclude inactive events (stalled, completed, cancelled or
        unresponsive)."""
        return self.exclude(tags__name="stalled").exclude(completed=True).not_cancelled().not_unresponsive()

    def past_events(self) -> "EventQuerySet":
        """Return past events.

        Past events are those which started before today, and
        which either ended before today or whose end is NULL
        """

        # All events that started before today
        queryset = self.filter(start__lt=datetime.date.today())

        # Of those events, only those that also ended before today
        # or where the end date is NULL
        ended_before_today = models.Q(end__lt=datetime.date.today())
        end_is_null = models.Q(end__isnull=True)

        queryset = queryset.filter(ended_before_today | end_is_null)

        return queryset

    def upcoming_events(self) -> "EventQuerySet":
        """Return published upcoming events.

        Upcoming events are published events (see `published_events` below)
        that start after today."""

        queryset = self.published_events().filter(start__gt=datetime.date.today()).order_by("start")
        return queryset

    def ongoing_events(self) -> "EventQuerySet":
        """Return ongoing events.

        Ongoing events are published events (see `published_events` below)
        that are currently taking place (ie. start today or before and end
        today or later)."""

        # All events that start before or on today, and finish after or on
        # today.
        queryset = (
            self.published_events()
            .filter(start__lte=datetime.date.today())
            .filter(end__gte=datetime.date.today())
            .order_by("start")
        )

        return queryset

    def current_events(self) -> "EventQuerySet":
        """Return current events.

        Current events are active ongoing events and active upcoming events
        (see `ongoing_events` and `upcoming_events` above).
        """
        queryset = self.upcoming_events() | self.ongoing_events()  # SQL UNION
        return queryset.active()

    def unpublished_conditional(self) -> Q:
        """Return conditional for events without: start OR country OR venue OR
        url OR are marked as 'cancelled' (ie. unpublished events). This will be
        used in `self.published_events`, too."""
        unknown_start = Q(start__isnull=True)
        no_country = Q(country__isnull=True)
        no_venue = Q(venue__exact="")
        no_address = Q(address__exact="")
        no_latitude = Q(latitude__isnull=True)
        no_longitude = Q(longitude__isnull=True)
        no_url = Q(url__isnull=True)
        return unknown_start | no_country | no_venue | no_address | no_latitude | no_longitude | no_url

    def unpublished_events(self) -> "EventQuerySet":
        """Return active events considered as unpublished (see
        `unpublished_conditional` above)."""
        conditional = self.unpublished_conditional()
        return self.active().filter(conditional).order_by("slug", "id").distinct()

    def published_events(self) -> "EventQuerySet":
        """Return events considered as published (see `unpublished_conditional`
        above)."""
        conditional = self.unpublished_conditional()
        return self.not_cancelled().exclude(conditional).order_by("-start", "id").distinct()

    def metadata_changed(self) -> "EventQuerySet":
        """Return events for which remote metatags have been updated."""
        return self.filter(metadata_changed=True)

    def ttt(self) -> "EventQuerySet":
        """Return only TTT events."""
        return self.filter(tags__name="TTT").distinct()

    def attendance(self) -> QuerySet[Annotated["Event", Annotations[EventAttendance]]]:
        """Instead of writing @cached_properties, that aren't available for
        DB operations, we'd rather count some numerical properties here using
        Django model annotations.

        attendance: it's the greatest value of (manually entered attendance,
        number of learner tasks).

        This is NOT a part of ModelManager.get_queryset, because I ran into
        Django bug (ticket???) that multiplied `filter` part (below) whenever
        the query chaining happened (the result was obtainable through
        `qs.query`), and resulted in SQLite error:
        django.db.utils.OperationalError: wrong number of arguments to function COUNT()
        """
        return self.annotate(learner_tasks_count=Count("task", filter=Q(task__role__name="learner"))).annotate(
            attendance=Greatest("manual_attendance", "learner_tasks_count"),
        )  # type: ignore


@reversion.register
class Event(AssignmentMixin, models.Model):
    """Represent a single event."""

    REPO_REGEX = re.compile(r"https?://github\.com/(?P<name>[^/]+)/(?P<repo>[^/]+)/?")
    REPO_FORMAT = "https://github.com/{name}/{repo}"
    WEBSITE_REGEX = re.compile(r"https?://(?P<name>[^.]+)\.github\.(io|com)/(?P<repo>[^/]+)/?")
    WEBSITE_FORMAT = "https://{name}.github.io/{repo}/"
    PUBLISHED_HELP_TEXT = 'Required in order for this event to be "published".'

    host = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        related_name="hosted_events",
        help_text="The institution where the workshop is taking place (or would take place for online workshops).",
    )
    # Currently this is organiser
    sponsor = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=False,
        related_name="sponsored_events",
        help_text="The institution responsible for organizing and funding the workshop (often the same as Host).",
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="The membership this workshop should count towards.",
    )
    administrator = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=False,
        related_name="administered_events",
        help_text="Lesson Program administered for this workshop.",
    )
    tags = models.ManyToManyField(
        Tag,
        help_text="<ul><li><i>stalled</i> — for events with lost contact with "
        "the host or TTT events that aren't running.</li>"
        "<li><i>unresponsive</i> – for events whose hosts and/or "
        "organizers aren't going to send us attendance data.</li>"
        "<li><i>cancelled</i> — for events that were supposed to "
        "happen, but due to some circumstances got cancelled.</li>"
        "</ul>",
    )
    start = models.DateField(null=True, blank=True, help_text=PUBLISHED_HELP_TEXT)
    end = models.DateField(null=True, blank=True)
    slug = models.SlugField(
        max_length=STR_LONG,
        unique=True,
        help_text="Use <code>YYYY-MM-DD-location</code> format, where "
        "<code>location</code> is either an organization, or city, "
        "or both. If the specific date is unknown, use "
        "<code>xx</code> instead, for example: <code>2016-12-xx"
        "-Krakow</code> means that the event is supposed to run "
        "sometime in December 2016 in Kraków. Use only latin "
        "characters.",
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Human language of instruction during the workshop.",
    )
    url = models.CharField(
        max_length=STR_LONG,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(REPO_REGEX, inverse_match=True)],
        help_text=PUBLISHED_HELP_TEXT + "<br />Use link to the event's <b>website</b>, " + "not repository.",
        verbose_name="URL",
    )
    reg_key = models.CharField(max_length=STR_REG_KEY, blank=True, verbose_name="Eventbrite key")
    manual_attendance = models.PositiveIntegerField(
        null=False,
        blank=True,
        default=0,
        verbose_name="Manual attendance",
        help_text="Manually entered attendance; for actual attendance, this "
        "number is compared with number of Learner tasks, and the "
        "higher value is shown.",
    )
    contact = models.CharField(
        max_length=STR_LONGEST,
        default="",
        blank=True,
        verbose_name="Additional people to contact",
    )
    country = CountryField(
        null=True,
        blank=True,
        help_text=PUBLISHED_HELP_TEXT
        + "<br />For Data, Library, or Software Carpentry workshops, always "
        + "use the country of the host organisation. <br />For Instructor "
        + "Training, use the country only for in-person events, and use "
        + "<b>Online</b> for online events. <br />Be sure to use the "
        + "<b>online tag</b> above for all online events.",
    )
    venue = models.CharField(
        max_length=STR_LONGEST,
        default="",
        blank=True,
        help_text=PUBLISHED_HELP_TEXT,
    )
    address = models.CharField(
        max_length=350,
        default="",
        blank=True,
        help_text=PUBLISHED_HELP_TEXT,
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text=PUBLISHED_HELP_TEXT,
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text=PUBLISHED_HELP_TEXT,
    )

    completed = models.BooleanField(
        default=False,
        help_text="Indicates that no more work is needed upon this event.",
    )

    # links to the surveys
    learners_pre = models.URLField(
        blank=True,
        default="",
        verbose_name="Pre-workshop assessment survey for learners",
    )
    learners_post = models.URLField(
        blank=True,
        default="",
        verbose_name="Post-workshop assessment survey for learners",
    )
    instructors_pre = models.URLField(
        blank=True,
        default="",
        verbose_name="Pre-workshop assessment survey for instructors",
    )
    instructors_post = models.URLField(
        blank=True,
        default="",
        verbose_name="Post-workshop assessment survey for instructors",
    )
    learners_longterm = models.URLField(blank=True, default="", verbose_name="Long-term assessment survey for learners")

    # used in getting metadata updates from GitHub
    repository_last_commit_hash = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Event's repository last commit SHA1 hash",
    )
    repository_metadata = models.TextField(
        blank=True,
        default="",
        help_text="JSON-serialized metadata from event's website",
    )
    metadata_all_changes = models.TextField(blank=True, default="", help_text="List of detected metadata changes")
    metadata_changed = models.BooleanField(default=False, help_text="Indicate if metadata changed since last check")

    # defines if people not associated with specific member sites can take part
    # in TTT event
    open_TTT_applications = models.BooleanField(
        null=False,
        blank=True,
        default=False,
        verbose_name="TTT Open applications",
        help_text="If this event is <b>TTT</b>, you can mark it as 'open "
        "applications' which means that people not associated with "
        "this event's member sites can also take part in this event.",
    )

    # taught curriculum information
    curricula = models.ManyToManyField["Curriculum", Any](
        "Curriculum",
        blank=True,
        limit_choices_to={"active": True, "unknown": False},
        verbose_name="Curricula taught at the workshop",
    )
    lessons = models.ManyToManyField["Lesson", Any](
        "Lesson",
        blank=True,
        verbose_name="Lessons covered",
        help_text="Specific lessons covered during the event",
    )

    # indicate that the workshop is either private or public
    PUBLIC_STATUS_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
    ]
    public_status = models.CharField(
        max_length=10,
        choices=PUBLIC_STATUS_CHOICES,
        default="public",
        blank=True,
        verbose_name="Is this workshop public?",
        help_text="Public workshops will show up in public Carpentries feeds.",
    )

    event_category = models.ForeignKey("EventCategory", on_delete=models.PROTECT, null=True, blank=True)

    objects = EventQuerySet.as_manager()

    allocated_benefit = models.ForeignKey(
        "offering.AccountBenefit",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
        verbose_name="Allocated account benefit (of type 'event')",
        limit_choices_to=Q(benefit__unit_type="event"),
    )

    class Meta:
        ordering = ("-start",)

    def __str__(self) -> str:
        return self.slug

    def get_absolute_url(self) -> str:
        return reverse("event_details", args=[self.slug])

    @cached_property
    def repository_url(self) -> str:
        """Return self.url formatted as it was repository URL.

        Repository URL is as specified in REPO_FORMAT.
        If it doesn't match, the original URL is returned."""
        try:
            # Try to match repo regex first. This will result in all repo URLs
            # always formatted in the same way.
            mo = self.REPO_REGEX.match(self.url) or self.WEBSITE_REGEX.match(self.url)  # type: ignore
            if not mo:
                return self.url  # type: ignore

            return self.REPO_FORMAT.format(**mo.groupdict())
        except (TypeError, KeyError):
            # TypeError: self.url is None
            # KeyError: mo.groupdict doesn't supply required names to format
            return self.url  # type: ignore

    @cached_property
    def website_url(self) -> str:
        """Return self.url formatted as it was website URL.

        Website URL is as specified in WEBSITE_FORMAT.
        If it doesn't match, the original URL is returned."""
        try:
            # Try to match website regex first. This will result in all website
            # URLs always formatted in the same way.
            mo = self.WEBSITE_REGEX.match(self.url) or self.REPO_REGEX.match(self.url)  # type: ignore
            if not mo:
                return self.url  # type: ignore

            return self.WEBSITE_FORMAT.format(**mo.groupdict())
        except (TypeError, KeyError):
            # TypeError: self.url is None
            # KeyError: mo.groupdict doesn't supply required names to format
            return self.url  # type: ignore

    @cached_property
    def mailto(self) -> list[str]:
        """Return list of emails we can contact about workshop details, like
        attendance."""
        emails = find_emails(self.contact)
        return emails

    def human_readable_date(self, **kwargs: Any) -> str:
        """Render start and end dates as human-readable short date."""
        date1 = self.start
        date2 = self.end
        return human_daterange(date1, date2, **kwargs)

    @cached_property
    def attendance(self) -> int:
        """This completes the "manually" appended .attendance() annotation.

        It's useful e.g. in cases when we access a single object that wasn't
        annotated this way before."""
        return max([self.manual_attendance, self.task_set.filter(role__name="learner").count()])

    def eligible_for_instructor_recruitment(self) -> bool:
        return bool(
            self.start
            and self.start >= datetime.date.today()
            and (
                self.venue
                and self.latitude is not None
                and self.longitude is not None
                or "online" in self.tags.strings()
            )
        )

    def workshop_reports_link(self) -> str:
        return reports_link(str(self.slug))

    def clean(self) -> None:
        """Additional model validation."""

        # Applies only to saved model instances!!! Otherwise it's impossible
        # to access M2M objects.
        if self.pk:
            errors = dict()
            has_TTT = self.tags.filter(name="TTT")

            if self.open_TTT_applications and not has_TTT:
                errors["open_TTT_applications"] = "You cannot open applications on non-TTT event."

            if errors:
                raise ValidationError(errors)
        # additional validation before the object is saved is in EventForm

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.slug = self.slug or None  # type: ignore
        self.url = self.url or None

        if self.country == "W3":
            # enforce location data for 'Online' country
            self.venue = "Internet"
            self.address = "Internet"
            self.latitude = None
            self.longitude = None

        if self.slug and not self.completed:
            self.instructors_pre = reports_link(self.slug)

        super().save(*args, **kwargs)


# ------------------------------------------------------------


class EventCategory(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """Describe category of event. Part of Service Offering Model 2025."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=STR_LONG)
    description = models.CharField(max_length=STR_LONGEST)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("event-category-details", kwargs={"pk": self.pk})


# ------------------------------------------------------------


class Role(models.Model):
    """Enumerate roles in workshops."""

    name = models.CharField(max_length=STR_MED)
    verbose_name = models.CharField(max_length=STR_LONG, null=False, blank=True, default="")

    def __str__(self) -> str:
        return self.verbose_name


# ------------------------------------------------------------


class TaskManager(models.Manager["Task"]):
    def instructors(self) -> QuerySet["Task"]:
        """Fetch tasks with role 'instructor'."""
        return self.get_queryset().filter(role__name="instructor")

    def learners(self) -> QuerySet["Task"]:
        """Fetch tasks with role 'learner'."""
        return self.get_queryset().filter(role__name="learner")

    def helpers(self) -> QuerySet["Task"]:
        """Fetch tasks with role 'helper'."""
        return self.get_queryset().filter(role__name="helper")


@reversion.register
class Task(models.Model):
    """Represent who did what at events."""

    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    seat_membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
        verbose_name="Associated member site in TTT event",
        help_text="In order to count this person into number of used "
        "membership instructor training seats, a correct membership "
        "entry needs to be selected.",
    )
    SEAT_PUBLIC_CHOICES = (
        (True, "Public seat"),
        (False, "In-house seat"),
    )
    seat_public = models.BooleanField(
        null=False,
        blank=True,
        default=True,
        choices=SEAT_PUBLIC_CHOICES,
        verbose_name="Count seat as public or in-house?",
        help_text="Ignored if the task is not for membership seat.",
    )
    seat_open_training = models.BooleanField(
        null=False,
        blank=True,
        default=False,
        verbose_name="Open training seat",
        help_text="Some TTT events allow for open training; check this field "
        "to count this person into open applications.",
    )
    allocated_benefit = models.ForeignKey(
        "offering.AccountBenefit",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
        verbose_name="Allocated account benefit (of type 'seat')",
        limit_choices_to=Q(benefit__unit_type="seat"),
    )

    objects = TaskManager()

    class Meta:
        unique_together = ("event", "person", "role")
        ordering = ("role__name", "event")

    def __str__(self) -> str:
        return "{0}/{1}={2}".format(self.event, self.person, self.role)

    def get_absolute_url(self) -> str:
        return reverse("task_details", kwargs={"task_id": self.pk})

    def clean(self) -> None:
        """Additional model validation."""

        # check seats, make sure the corresponding event has "TTT" tag
        errors = dict()
        try:
            has_ttt = bool(self.event.tags.filter(name="TTT"))
            is_open_app = self.event.open_TTT_applications
        except Event.DoesNotExist:
            has_ttt = False
            is_open_app = False

        if self.seat_membership is not None and self.seat_open_training:
            raise ValidationError(
                "This Task cannot be simultaneously open training and use a Membership instructor training seat."
            )

        if not has_ttt and self.seat_membership is not None:
            errors["seat_membership"] = ValidationError(
                "Cannot associate membership when the event has no TTT tag",
                code="invalid",
            )

        if not has_ttt and self.seat_open_training:
            errors["seat_open_training"] = ValidationError(
                "Cannot mark this person as open applicant, because the event has no TTT tag.",
                code="invalid",
            )
        elif has_ttt and not is_open_app and self.seat_open_training:
            errors["seat_open_training"] = ValidationError(
                "Cannot mark this person as open applicant, because the TTT "
                "event is not marked as open applications.",
                code="invalid",
            )

        if (self.seat_membership or self.seat_open_training) and self.role.name != "learner":
            errors["role"] = ValidationError("Seat (open / membership) can be assigned only to a workshop learner.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)
        # Trigger an update of the attendance field
        self.event.save()


# ------------------------------------------------------------


class Lesson(models.Model):
    """Represent a lesson someone might teach."""

    name = models.CharField(max_length=STR_MED)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]


# ------------------------------------------------------------


class Qualification(models.Model):
    """What is someone qualified to teach?"""

    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return "{0}/{1}".format(self.person, self.lesson)


# ------------------------------------------------------------


class BadgeQuerySet(QuerySet["Badge"]):
    """Custom QuerySet that provides easy way to get instructor badges
    (we use that a lot)."""

    SINGLE_INSTRUCTOR_BADGE = "instructor"

    INSTRUCTOR_BADGES = (
        "dc-instructor",
        "swc-instructor",
        "lc-instructor",
        SINGLE_INSTRUCTOR_BADGE,
    )

    TRAINER_BADGE = "trainer"

    def instructor_badges(self) -> QuerySet["Badge"]:
        """Filter for instructor badges only."""

        return self.filter(name__in=self.INSTRUCTOR_BADGES)


class Badge(models.Model):
    """Represent a badge we award."""

    # just for easier access outside `models.py`
    SINGLE_INSTRUCTOR_BADGE = BadgeQuerySet.SINGLE_INSTRUCTOR_BADGE
    INSTRUCTOR_BADGES = BadgeQuerySet.INSTRUCTOR_BADGES
    TRAINER_BADGE = BadgeQuerySet.TRAINER_BADGE
    IMPORTANT_BADGES = (SINGLE_INSTRUCTOR_BADGE, TRAINER_BADGE)

    name = models.CharField(max_length=STR_MED, unique=True)
    title = models.CharField(max_length=STR_MED)
    criteria = models.CharField(max_length=STR_LONG)

    objects = Manager.from_queryset(BadgeQuerySet)()

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("badge_details", args=[self.name])


# ------------------------------------------------------------


class Award(models.Model):
    """Represent a particular badge earned by a person."""

    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    badge = models.ForeignKey(Badge, on_delete=models.PROTECT)
    awarded = models.DateField(default=datetime.date.today)
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.PROTECT)
    awarded_by = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="awarded_set",
    )

    class Meta:
        unique_together = (
            "person",
            "badge",
        )
        ordering = ["awarded"]

    def __str__(self) -> str:
        return "{0}/{1}/{2}/{3}".format(self.person, self.badge, self.awarded, self.event)

    def get_absolute_url(self) -> str:
        return reverse("person_details", args=[self.person.pk])


# ------------------------------------------------------------


class KnowledgeDomain(models.Model):
    """Represent a knowledge domain a person is engaged in."""

    name = models.CharField(max_length=STR_LONG)
    # TODO: migrate to Boolean `unknown`

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]


# ------------------------------------------------------------


class CurriculumType(models.Model):
    """Describe category of curriculum. Part of Service Offering Model 2025."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program_category = models.CharField(max_length=STR_LONG)
    name = models.CharField(max_length=STR_LONG)
    description = models.CharField(max_length=STR_LONGEST)

    def __str__(self) -> str:
        return self.name


# ------------------------------------------------------------


class CurriculumManager(models.Manager["Curriculum"]):
    def default_order(
        self,
        allow_unknown: bool = True,
        allow_other: bool = True,
        allow_mix_match: bool = False,
        dont_know_yet_first: bool = False,
    ) -> QuerySet["Curriculum"]:
        """A specific order_by() clause with semi-ninja code."""

        # This crazy django-ninja-code gives different weights to entries
        # matching different criterias, and then sorts them by 'name'.
        # For example when two entries (e.g. swc-r and swc-python) have the
        # same weight (here: 10), then sorting by name comes in.
        # Entries dc-other, swc-other, lc-other, or `I don't know` are made
        # last of their "group".
        qs = self.order_by(
            Case(
                When(carpentry="SWC", other=False, then=10),
                When(carpentry="SWC", other=True, then=15),
                When(carpentry="DC", other=False, then=20),
                When(carpentry="DC", other=True, then=25),
                When(carpentry="LC", other=False, then=30),
                When(carpentry="LC", other=True, then=35),
                When(unknown=True, then=1 if dont_know_yet_first else 200),
                When(carpentry="", then=100),
                default=1,
            ),
            "name",
        )

        # conditionally disable unknown ("I don't know") entry from appearing
        # in the list
        if not allow_unknown:
            qs = qs.filter(unknown=False)

        # conditionally disable other entries (swc-other, etc.) from appearing
        # in the list
        if not allow_other:
            qs = qs.filter(other=False)

        # conditionally disable Mix&Match entry from appearing in the list
        if not allow_mix_match:
            qs = qs.filter(mix_match=False)

        return qs


class Curriculum(ActiveMixin, models.Model):
    CARPENTRIES_CHOICES = (
        ("SWC", "Software Carpentry"),
        ("DC", "Data Carpentry"),
        ("LC", "Library Carpentry"),
        ("", "unspecified / irrelevant"),
    )
    carpentry = models.CharField(
        max_length=5,
        choices=CARPENTRIES_CHOICES,
        null=False,
        blank=True,
        default="",
        verbose_name="Which Carpentry does this curriculum belong to?",
    )
    slug = models.CharField(
        max_length=STR_MED,
        null=False,
        blank=False,
        default="",
        unique=True,
        verbose_name="Curriculum ID",
        help_text="Use computer-friendly text here, e.g. 'dc-ecology-r'.",
    )
    name = models.CharField(
        max_length=200,
        null=False,
        blank=False,
        default="",
        unique=True,
        verbose_name="Curriculum name",
        help_text="Use user-friendly language, e.g. 'Data Carpentry (Ecology with R)'.",
    )
    description = models.TextField(
        max_length=400,
        null=False,
        blank=True,
        default="",
        verbose_name="Curriculum longer description",
        help_text="You can enter Markdown. It will be shown as a hover or popup over the curriculum entry on forms.",
    )
    other = models.BooleanField(
        null=False,
        blank=True,
        default=False,
        verbose_name="Field marked as 'Other'",
        help_text="Mark this curriculum record as '*Other' (eg. 'SWC Other', 'DC Other', or simply 'Other')",
    )
    unknown = models.BooleanField(
        null=False,
        blank=True,
        default=False,
        verbose_name="Unknown entry",
        help_text="Mark this curriculum record as 'I don't know yet', or "
        "'Unknown', or 'Not sure yet'. There can be only one such "
        "record in the database.",
    )
    mix_match = models.BooleanField(
        null=False,
        blank=True,
        default=False,
        verbose_name="Mix & Match",
        help_text="Mark this curriculum record as 'Mix & Match'.There can be only one such record in the database.",
    )
    website = models.URLField(
        blank=True,
        default="",
        verbose_name="Curriculum page",
    )

    objects = CurriculumManager()

    class Meta:
        verbose_name = "Curriculum"
        verbose_name_plural = "Curricula"
        ordering = [
            "slug",
        ]

    def __str__(self) -> str:
        return self.name

    @transaction.atomic
    def save(self, *args: Any, **kwargs: Any) -> None:
        """When saving with `unknown=True`, update all other records with this
        parameter to `unknown=False`. This helps keeping only one record with
        `unknown=True` in the database - a specific case of uniqueness."""

        # wrapped in transaction in order to prevent from updating records to
        # `unknown=False` when saving fails
        if self.unknown:
            Curriculum.objects.filter(unknown=True).update(unknown=False)
        # same for mix_match
        if self.mix_match:
            Curriculum.objects.filter(mix_match=True).update(mix_match=False)
        return super().save(*args, **kwargs)


# ------------------------------------------------------------


class TrainingRequestManager(models.Manager["TrainingRequest"]):
    def get_queryset(self) -> QuerySet["TrainingRequest"]:
        """Enhance default TrainingRequest queryset with auto-computed
        fields."""
        return (
            super()
            .get_queryset()
            .annotate(
                score_total=Case(
                    When(
                        score_manual__isnull=False,
                        then=F("score_auto") + F("score_manual"),
                    ),
                    When(score_manual__isnull=True, then=F("score_auto")),
                    output_field=PositiveIntegerField(),
                ),
            )
        )


@reversion.register
class TrainingRequest(
    CreatedUpdatedMixin,
    DataPrivacyAgreementMixin,
    COCAgreementMixin,
    StateExtendedMixin,
    SecondaryEmailMixin,
    models.Model,
):
    MANUAL_SCORE_UPLOAD_FIELDS = (
        "request_id",
        "score_manual",
        "score_notes",
    )

    person = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        verbose_name="Matched Trainee",
        on_delete=models.SET_NULL,
    )

    REVIEW_CHOICES = (
        ("preapproved", "Profile Creation for Pre-approved Trainees"),
        ("open", "Open Training Application"),
    )
    REVIEW_CHOICES_NOTES = {
        "preapproved": (
            "Use this if you have been invited to apply through an"
            " institutional membership or other agreement with The"
            " Carpentries. Please note your application materials and"
            " information about your progress towards The Carpentries"
            " Instructor certification may be shared with our contacts at your"
            " member site."
        ),
        "open": (
            "Submit application for review to receive a scholarship for"
            " Instructor Training through our Open Application Program. Please"
            " note your application materials may be shared with The"
            " Carpentries Trainers in order to review and accept your"
            " application."
        ),
    }
    review_process = models.CharField(
        blank=False,
        default="",
        null=False,
        max_length=20,
        choices=REVIEW_CHOICES,
        verbose_name="Application Type",
    )

    member_code = models.CharField(
        blank=True,
        default="",
        null=False,
        max_length=STR_LONG,
        verbose_name="Registration Code",
        help_text="If you have been given a registration code through "
        "a Carpentries member site or for a specific scheduled "
        "event, please enter it here:",
    )
    member_code_override = models.BooleanField(
        null=False,
        default=False,
        blank=True,
        verbose_name="Continue with registration code marked as invalid",
        help_text="A member of our team will check the code and follow up with you if "
        "there are any problems that require your attention.",
    )
    eventbrite_url = models.URLField(
        null=False,
        blank=True,
        default="",
        verbose_name="Eventbrite URL",
        help_text="If you are registering or have registered for a training event "
        "through Eventbrite, enter the URL of that event. You can find this on the "
        "registration page or in the confirmation email. "
        "If you have not yet registered for an event, leave this field blank.",
    )

    personal = models.CharField(
        max_length=STR_LONG,
        verbose_name="Personal (given) name",
        blank=False,
    )
    middle = models.CharField(
        max_length=STR_LONG,
        verbose_name="Middle name",
        blank=True,
    )
    family = models.CharField(
        max_length=STR_LONG,
        verbose_name="Family name (surname)",
        blank=True,
    )

    email = models.EmailField(
        verbose_name="Email address",
        blank=False,
    )
    github = NullableGithubUsernameField(
        verbose_name="GitHub username",
        help_text="Please put only a single username here. After your application has "
        "been accepted, you will be able to use your GitHub username to log in to our "
        "database to view your profile.",
        null=True,
        blank=True,
    )

    OCCUPATION_CHOICES = (
        ("undisclosed", "Prefer not to say"),
        ("undergrad", "Undergraduate student"),
        ("grad", "Graduate student"),
        ("postdoc", "Post-doctoral researcher"),
        ("faculty", "Faculty"),
        ("research", "Research staff (including research programmer)"),
        ("support", "Support staff (including technical support)"),
        ("librarian", "Librarian/archivist"),
        ("commerce", "Commercial software developer "),
        ("", "Other:"),
    )
    occupation = models.CharField(
        max_length=STR_MED,
        choices=OCCUPATION_CHOICES,
        verbose_name="What is your current occupation/career stage?",
        help_text="Please choose the one that best describes you.",
        blank=True,
        default="undisclosed",
    )
    occupation_other = models.CharField(
        max_length=STR_LONG,
        verbose_name="Other occupation/career stage",
        blank=True,
        default="",
    )

    affiliation = models.CharField(
        max_length=STR_LONG,
        verbose_name="Affiliation",
        null=False,
        blank=False,
    )

    location = models.CharField(
        max_length=STR_LONG,
        verbose_name="Location",
        help_text="Please give city, and province or state if applicable. Do not share a full mailing address.",
        blank=False,
    )
    country = CountryField()
    underresourced = models.BooleanField(
        null=False,
        default=False,
        blank=True,
        verbose_name="This is a small, remote, or under-resourced institution",
        help_text="The Carpentries strive to make workshops accessible to as "
        "many people as possible, in as wide a variety of situations"
        " as possible.",
    )

    domains = models.ManyToManyField["KnowledgeDomain", Any](
        "KnowledgeDomain",
        verbose_name="Areas of expertise",
        help_text="Please check all that apply.",
        limit_choices_to=~Q(name__startswith="Don't know yet"),
        blank=True,
    )
    domains_other = models.CharField(
        max_length=STR_LONGEST,
        verbose_name="Other areas of expertise",
        blank=True,
        default="",
    )

    UNDERREPRESENTED_CHOICES = (
        ("yes", "Yes"),
        ("no", "No"),
        ("undisclosed", "Prefer not to say"),
    )
    underrepresented = models.CharField(
        max_length=20,
        blank=False,
        default="undisclosed",
        choices=UNDERREPRESENTED_CHOICES,
        verbose_name="I self-identify as a member of a group that is "
        "under-represented in research and/or computing.",
        help_text="The Carpentries strives to increase opportunities for underrepresented groups to join our team.",
    )
    underrepresented_details = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        default="",
        verbose_name="If you are comfortable doing so, please share more details.",
        help_text="This response is optional and doesn't impact your application's ranking.",
    )

    # teaching-related experience in non-profit or volunteer org
    nonprofit_teaching_experience = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        default="",
        verbose_name="I have been an active contributor to other volunteer or"
        " non-profit groups with significant teaching or training"
        " components.",
        help_text="Provide details or leave blank if this doesn't apply to you.",
    )

    previous_involvement = models.ManyToManyField["Role", Any](
        "Role",
        verbose_name="In which of the following ways have you been involved with The Carpentries",
        help_text="Please check all that apply.",
        blank=True,
    )

    PREVIOUS_TRAINING_CHOICES = (
        ("none", "None"),
        ("hours", "A few hours"),
        ("workshop", "A workshop"),
        ("course", "A certification or short course"),
        ("full", "A full degree"),
        ("other", "Other:"),
    )
    previous_training, previous_training_other = choice_field_with_other(
        choices=PREVIOUS_TRAINING_CHOICES,
        verbose_name="Previous formal training as a teacher or instructor",
        default="none",
    )
    previous_training_explanation = models.TextField(
        verbose_name="Description of your previous training in teaching",
        blank=True,
        default="",
    )

    # this part changed a little bit, mostly wording and choices
    PREVIOUS_EXPERIENCE_CHOICES = (
        ("none", "None"),
        ("hours", "A few hours"),
        ("workshop", "A workshop (full day or longer)"),
        ("ta", "Teaching assistant for a full course"),
        ("courses", "Primary instructor for a full course"),
        ("other", "Other:"),
    )
    (
        previous_experience,
        previous_experience_other,
    ) = choice_field_with_other(
        choices=PREVIOUS_EXPERIENCE_CHOICES,
        default="none",
        verbose_name="Previous experience in teaching",
        help_text="Please include teaching experience at any level from grade school to post-secondary education.",
    )
    previous_experience_explanation = models.TextField(
        verbose_name="Description of your previous experience in teaching",
        blank=True,
        default="",
    )

    PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES = (
        ("daily", "Every day"),
        ("weekly", "A few times a week"),
        ("monthly", "A few times a month"),
        ("yearly", "A few times a year"),
        ("not-much", "Never or almost never"),
    )
    programming_language_usage_frequency = models.CharField(
        max_length=STR_MED,
        choices=PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES,
        verbose_name="How frequently do you work with the tools that The "
        "Carpentries teach, such as R, Python, MATLAB, Perl, "
        "SQL, Git, OpenRefine, and the Unix Shell?",
        null=False,
        blank=False,
        default="daily",
    )

    CHECKOUT_INTENT_CHOICES = (
        ("yes", "Yes"),
        ("no", "No"),
        ("unsure", "Not sure"),
    )
    checkout_intent = models.CharField(
        max_length=STR_MED,
        choices=CHECKOUT_INTENT_CHOICES,
        verbose_name="Do you intend to complete The Carpentries checkout process to be "
        "certified as a Carpentries Instructor?",
        help_text="The checkout process is described on our "
        '<a href="https://carpentries.github.io/instructor-training/checkout.html">'
        "Checkout Instructions</a> page.",
        null=False,
        blank=False,
        default="unsure",
    )

    TEACHING_INTENT_CHOICES = (
        (
            "yes-local",
            "Yes - I plan to teach Carpentries workshops in my local community or personal networks",
        ),
        (
            "yes-central",
            "Yes - I plan to volunteer with The Carpentries to teach workshops for other communities",
        ),
        (
            "yes-either",
            "Yes - either or both of the above",
        ),
        ("no", "No"),
        ("unsure", "Not sure"),
    )
    teaching_intent = models.CharField(
        max_length=STR_MED,
        choices=TEACHING_INTENT_CHOICES,
        verbose_name="Do you intend to teach Carpentries workshops within the next 12 months?",
        null=False,
        blank=False,
        default="unsure",
    )

    TEACHING_FREQUENCY_EXPECTATION_CHOICES = (
        ("not-at-all", "Not at all"),
        ("yearly", "Once a year"),
        ("monthly", "Several times a year"),
        ("other", "Other:"),
    )
    (
        teaching_frequency_expectation,
        teaching_frequency_expectation_other,
    ) = choice_field_with_other(
        choices=TEACHING_FREQUENCY_EXPECTATION_CHOICES,
        verbose_name="How often would you expect to teach Carpentries workshops  (of any kind) after this training?",
        default="not-at-all",
    )

    MAX_TRAVELLING_FREQUENCY_CHOICES = (
        ("not-at-all", "Not at all"),
        ("yearly", "Once a year"),
        ("often", "Several times a year"),
        ("other", "Other:"),
    )
    (
        max_travelling_frequency,
        max_travelling_frequency_other,
    ) = choice_field_with_other(
        choices=MAX_TRAVELLING_FREQUENCY_CHOICES,
        verbose_name="How frequently would you be able to travel to teach such classes?",
        default="not-at-all",
    )

    reason = models.TextField(
        verbose_name="Why do you want to attend this training course?",
        null=False,
        blank=False,
    )

    user_notes = models.TextField(
        default="",
        null=False,
        blank=True,
        help_text="What else do you want us to know?",
        verbose_name="Anything else?",
    )

    score_auto = models.PositiveIntegerField(
        null=False,
        blank=False,
        default=0,
        verbose_name="Application automatic score",
        help_text="Filled out by AMY.",
    )
    score_manual = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Application manual score (can be negative)",
        help_text="Leave blank if you don't want to score this application.",
    )
    # score_total - calculated automatically by the manager
    score_notes = models.TextField(
        blank=True,
        verbose_name="Notes regarding manual score",
        help_text="Explanation of manual score, if necessary.",
    )

    objects = TrainingRequestManager()

    class Meta:
        ordering = ["created_at"]

    def clean(self) -> None:
        super().clean()

        if self.state == "p" and self.person is not None and self.person.get_training_tasks().exists():
            raise ValidationError({"state": "Pending training request cannot be matched with a training."})

    def recalculate_score_auto(self) -> int:
        """Calculate automatic score according to the rubric:
        https://github.com/carpentries/instructor-training/blob/gh-pages/files/rubric.md
        """
        score = 0

        # location based points (country not on the list of countries)
        # according to
        # https://github.com/swcarpentry/amy/issues/1327#issuecomment-422539917
        # and
        # https://github.com/swcarpentry/amy/issues/1327#issuecomment-423292177
        not_scoring_countries = [
            "US",
            "CA",
            "NZ",
            "GB",
            "AU",
            "AT",
            "BE",
            "CY",
            "CZ",
            "DK",
            "EE",
            "FI",
            "FR",
            "DE",
            "GR",
            "HU",
            "IE",
            "IT",
            "LV",
            "LT",
            "LU",
            "MT",
            "NL",
            "PL",
            "PT",
            "RO",
            "SK",
            "SI",
            "ES",
            "SE",
            "CH",
            "IS",
            "NO",
        ]
        if self.country and self.country.code not in not_scoring_countries:
            score += 1

        if self.underresourced:
            score += 1

        # economics or social sciences, arts, humanities, library science, or
        # chemistry
        scoring_domains = [
            "Humanities",
            "Library and information science",
            "Economics/business",
            "Social sciences",
            "Chemistry",
        ]
        for domain in self.domains.all():
            if domain.name in scoring_domains:
                score += 1
                break

        # Changed in https://github.com/swcarpentry/amy/issues/1468:
        # +1 for underrepresented minority in research and/or computing
        if self.underrepresented == "yes":
            score += 1

        # +1 for each previous involvement with The Carpentries (max. 3)
        prev_inv_count = len(self.previous_involvement.all())
        score += prev_inv_count if prev_inv_count <= 3 else 3

        # previous training in teaching: "a certification or short course"
        # or "a full degree"
        if self.previous_training in ["course", "full"]:
            score += 1

        # previous experience in teaching: "TA for full course"
        # or "primary instructor for full course"
        if self.previous_experience in ["ta", "courses"]:
            score += 1

        # using tools "every day" or "a few times a week"
        if self.programming_language_usage_frequency in ["daily", "weekly"]:
            score += 1

        return score

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Run recalculation upon save."""
        inserted = False

        # save first so that there's an ID present
        if not self.pk:
            super().save(*args, **kwargs)
            inserted = True

        score = self.recalculate_score_auto()

        if self.pk and score != self.score_auto:
            self.score_auto = score

        # we cannot force insert for the second time - this time it should
        # be an UPDATE query
        if inserted and "force_insert" in kwargs:
            kwargs.pop("force_insert")

        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("trainingrequest_details", args=[self.pk])

    def __str__(self) -> str:
        return "{personal} {family} <{email}> - {state}".format(
            state=self.get_state_display(),
            personal=self.personal,
            family=self.family,
            email=self.email,
        )


@reversion.register
class TrainingRequirement(models.Model):
    name = models.CharField(max_length=STR_MED)

    # Determines whether TrainingProgress.url is required (True) or must be
    # null (False).
    url_required = models.BooleanField(default=False)

    # Determines whether TrainingProgress.event is required (True) or must be
    # null (False).
    event_required = models.BooleanField(default=False)

    # Determines whether TrainingProgress.involvement_type is required (True) or must be
    # null (False).
    involvement_required = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]


@reversion.register
class TrainingProgress(CreatedUpdatedMixin, models.Model):
    trainee = models.ForeignKey(Person, on_delete=models.PROTECT)

    date = models.DateField(
        verbose_name="Date of occurrence",
        help_text="Format: YYYY-MM-DD",
        null=True,
        blank=True,
    )
    requirement = models.ForeignKey(TrainingRequirement, on_delete=models.PROTECT, verbose_name="Type")

    STATES = (
        ("n", "Not evaluated yet"),
        ("f", "Failed"),
        ("p", "Passed"),
        ("a", "Asked to repeat"),
    )
    state = models.CharField(choices=STATES, default="p", max_length=1)

    involvement_type = models.ForeignKey(
        Involvement,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name="Type of involvement",
    )
    event = models.ForeignKey(
        Event,
        null=True,
        blank=True,
        verbose_name="Training",
        limit_choices_to=Q(tags__name="TTT"),
        on_delete=models.SET_NULL,
    )
    url = models.URLField(null=True, blank=True, verbose_name="URL")
    trainee_notes = models.CharField(
        blank=True,
        null=False,
        default="",
        max_length=STR_LONGEST,
        verbose_name="Notes from trainee",
    )
    notes = models.TextField(blank=True)

    def get_absolute_url(self) -> str:
        return reverse("trainingprogress_edit", args=[str(self.id)])

    def get_human_friendly_type(self, item: TrainingRequirement | Involvement) -> str:
        human_friendly_type_names = {
            TrainingRequirement: "progress type",
            Involvement: "activity",
        }
        return human_friendly_type_names.get(type(item), "")

    def get_required_error(self, item: TrainingRequirement | Involvement) -> ValidationError:
        item_type = self.get_human_friendly_type(item)
        return ValidationError(f'This field is required for {item_type} "{item}".')

    def get_not_required_error(self, item: TrainingRequirement | Involvement) -> ValidationError:
        item_type = self.get_human_friendly_type(item)
        return ValidationError(f'This field must be empty for {item_type} "{item}".')

    def clean_url(
        self,
        requirement: TrainingRequirement,
        involvement_type: Involvement | None = None,
    ) -> ValidationError | None:
        """A URL may be required by either a TrainingRequirement or an Involvement.
        If a TrainingRequirement does not require a URL or an Involvement, it is not
        permitted to enter a URL.
        Where an Involvement is required, URLs are always permitted, even if the
        specific Involvement chosen does not require one.
        """
        if self.url:
            if not requirement.url_required and not requirement.involvement_required and involvement_type:
                return self.get_not_required_error(involvement_type)
        else:
            if requirement.url_required:
                return self.get_required_error(requirement)

            elif requirement.involvement_required and involvement_type and involvement_type.url_required:
                return self.get_required_error(involvement_type)
        return None

    def clean_event(
        self,
        requirement: TrainingRequirement,
        involvement_type: Involvement | None = None,
    ) -> ValidationError | None:
        """An event can only be required by a TrainingRequirement."""
        if requirement.event_required and not self.event:
            return self.get_required_error(requirement)

        elif not requirement.event_required and self.event:
            return self.get_not_required_error(requirement)
        return None

    def clean_involvement_type(
        self,
        requirement: TrainingRequirement,
        involvement_type: Involvement | None = None,
    ) -> ValidationError | None:
        if requirement.involvement_required and not involvement_type:
            return self.get_required_error(requirement)

        elif not requirement.involvement_required and involvement_type:
            return self.get_not_required_error(requirement)
        return None

    def clean_date(
        self,
        requirement: TrainingRequirement,
        involvement_type: Involvement | None = None,
    ) -> ValidationError | None:
        """A date can only be required by an Involvement.
        The date must be today or earlier."""
        if requirement.involvement_required and involvement_type:
            if involvement_type.date_required and not self.date:
                return self.get_required_error(involvement_type)

            elif not involvement_type.date_required and self.date:
                return self.get_not_required_error(involvement_type)

        elif not requirement.involvement_required and self.date:
            return self.get_not_required_error(requirement)

        # if other checks passed, verify that date is no later than today
        # (considering timezones ahead of UTC)
        if self.date and self.date > timezone.localdate(timezone=datetime.timezone(datetime.timedelta(hours=14))):
            msg = "Date must be in the past."
            return ValidationError(msg)
        return None

    def clean_notes(
        self,
        requirement: TrainingRequirement,
        involvement_type: Involvement | None = None,
    ) -> list[ValidationError]:
        """Admin notes can be required by an Involvement
        or by marking the state as failed."""
        errors = []
        if requirement.involvement_required and involvement_type:
            if involvement_type.notes_required and not self.trainee_notes and not self.notes:
                msg = (
                    f'This field is required for activity "{involvement_type}" '
                    "if there are no notes from the trainee."
                )
                errors.append(ValidationError(msg))

        if self.state == "f" and not self.notes:
            msg = "This field is required if the state is marked as failed."
            errors.append(ValidationError(msg))

        return errors

    def clean_fields(self, exclude: Collection[str] | None = None) -> None:
        super().clean_fields(exclude=exclude)
        errors: dict[str, list[ValidationError] | ValidationError | None] = {}

        # note: trainee_notes field is cleaned in GetInvolvedForm instead
        #       as it should not display errors in admin-facing forms
        validators = [
            ("url", self.clean_url),
            ("event", self.clean_event),
            ("involvement_type", self.clean_involvement_type),
            ("date", self.clean_date),
            ("notes", self.clean_notes),
        ]

        for field, validator in validators:
            if exclude and field in exclude:
                continue
            error = validator(self.requirement, self.involvement_type)
            if error:
                errors[field] = error

        if errors:
            raise ValidationError(errors)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["trainee", "event"],
                name="unique_trainee_at_event",
            )
        ]


# ------------------------------------------------------------


# This model should belong to extrequests app, but moving it is pain due to M2M
# relationship with WorkshopRequest.
class AcademicLevel(models.Model):
    name = models.CharField(max_length=STR_MED, null=False, blank=False)
    # TODO: migrate to Boolean `unknown`

    def __str__(self) -> str:
        return self.name


# This model should belong to extrequests app, but moving it is pain due to M2M
# relationship with WorkshopRequest.
class ComputingExperienceLevel(models.Model):
    # it's a long field because we need to store reasoning too, for example:
    # "Novice (uses a spreadsheet for data analysis rather than writing code)"
    name = models.CharField(max_length=STR_LONGEST, null=False, blank=False)

    def __str__(self) -> str:
        return self.name


class InfoSource(models.Model):
    """
    This class represents a single source of information about The Carpentries.
    These sources answer the question "where did you hear about TC?" - eg.
    "a colleague told me", etc.
    """

    name = models.CharField(
        max_length=300,
        null=False,
        blank=False,
        default="",
        unique=True,
        verbose_name="Name",
        help_text="Source description (eg. 'colleague told me')",
    )

    class Meta:
        verbose_name = "Information source"
        verbose_name_plural = "Information sources"
        ordering = [
            "id",
        ]

    def __str__(self) -> str:
        return self.name


class CommonRequest(SecondaryEmailMixin, models.Model):
    """
    Common fields used across all *Requests, ie.:
    * WorkshopRequest model
    * WorkshopInquiryRequest model
    * SelfOrganizedSubmission
    """

    personal = models.CharField(
        max_length=STR_LONGEST,
        blank=False,
        null=False,
        verbose_name="Personal (first) name",
    )
    family = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="Family (last) name",
    )
    email = models.EmailField(
        blank=False,
        null=False,
        verbose_name="Email address",
    )
    institution = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Institutional affiliation",
        help_text="If your institution isn't on the list, enter its name below the list.",
    )
    institution_other_name = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="If your institutional affiliation is not listed, please enter the name",
        help_text="Please enter institution name if it's not on the list above.",
    )
    institution_other_URL = models.URLField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="If your institutional affiliation is not listed, please enter the website",
        help_text="Please provide URL.",
    )
    institution_department = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="Department/School/Library affiliation (if applicable)",
    )

    member_code = models.CharField(
        max_length=STR_MED,
        blank=True,
        null=False,
        default="",
        verbose_name="Membership registration code",
        help_text="If you are affiliated with a Carpentries member organization, "
        "please enter the registration code associated with the membership. "
        "Your Member Affiliate can provide this.",
    )

    ONLINE_INPERSON_CHOICES = (
        ("online", "Online"),
        ("inperson", "In-person"),
        ("unsure", "Not sure"),
    )
    online_inperson = models.CharField(
        max_length=15,
        choices=ONLINE_INPERSON_CHOICES,
        blank=False,
        null=False,
        default="",
        verbose_name="Will this workshop be held online or in-person?",
    )

    WORKSHOP_LISTED_CHOICES = (
        (True, "Yes"),
        (False, "No"),
    )
    workshop_listed = models.BooleanField(
        null=False,
        default=True,
        blank=True,
        choices=WORKSHOP_LISTED_CHOICES,
        verbose_name="Would you like to have this workshop listed on our websites?",
        help_text='If selected "Yes", the workshop will be published on following '
        'websites: <a href="https://carpentries.org/">The Carpentries</a>,'
        ' <a href="https://datacarpentry.org/">Data Carpentry</a>,'
        ' <a href="https://software-carpentry.org/">Software Carpentry</a>,'
        ' <a href="https://librarycarpentry.org/">Library Carpentry</a>.',
    )
    PUBLIC_EVENT_CHOICES = (
        ("public", "This event is open to the public."),
        (
            "closed",
            "This event is open primarily to the people inside of my institution.",
        ),
        ("other", "Other:"),
    )
    public_event = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        default="",
        choices=PUBLIC_EVENT_CHOICES,
        verbose_name="Is this workshop open to the public?",
        help_text="Many of our workshops restrict registration to learners "
        "from the hosting institution. If your workshop will be open"
        " to registrants outside of your institution please let us "
        "know below.",
    )
    public_event_other = models.CharField(
        max_length=STR_LONGEST,
        null=False,
        blank=True,
        default="",
        verbose_name="Other (workshop open to the public)",
    )
    additional_contact = models.CharField(
        max_length=STR_LONGEST,
        null=False,
        blank=True,
        default="",
        verbose_name="Is there anyone you would like included on communication"
        " for this workshop? Please provide e-mail addresses.",
    )

    class Meta:
        abstract = True

    def host(self) -> Person | None:
        """
        Try to fetch matching host for the data stored in
        (personal, family, email) attributes.
        """
        try:
            return Person.objects.get(personal=self.personal, family=self.family, email=self.email)
        except Person.DoesNotExist:
            return None

    def host_organization(self) -> Organization | None:
        """Try to fetch matching host organization."""
        try:
            return Organization.objects.get(fullname=self.institution_other_name)
        except Organization.DoesNotExist:
            return None


@reversion.register
class WorkshopRequest(
    AssignmentMixin,
    StateMixin,
    CreatedUpdatedMixin,
    CommonRequest,
    DataPrivacyAgreementMixin,
    COCAgreementMixin,
    HostResponsibilitiesMixin,
    InstructorAvailabilityMixin,
    EventLinkMixin,
    models.Model,
):
    location = models.CharField(
        max_length=STR_LONGEST,
        blank=False,
        null=False,
        default="",
        verbose_name="Workshop location",
        help_text="City, state, or province.",
    )
    country = CountryField(
        null=False,
        blank=False,
        verbose_name="Country",
    )
    # This field is no longer needed, and is hidden in the form and templates.
    conference_details = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="Is this workshop part of conference or larger event?",
        help_text="If yes, please provide conference details (name, description).",
    )
    # In form, this is limited to Curricula without "Other/SWC/LC/DC Other"
    # and "I don't know yet" options
    SWC_LESSONS_LINK = '<a href="https://software-carpentry.org/lessons/">' "Software Carpentry lessons page</a>"
    DC_LESSONS_LINK = '<a href="http://www.datacarpentry.org/lessons/">' "Data Carpentry lessons page</a>"
    LC_LESSONS_LINK = '<a href="https://librarycarpentry.org/lessons/">' "Library Carpentry lessons page</a>"
    INQUIRY_FORM = reverse_lazy("workshop_inquiry")
    requested_workshop_types = models.ManyToManyField(
        Curriculum,
        limit_choices_to={"active": True},
        blank=False,
        verbose_name="Which Carpentries workshop are you requesting?",
        help_text=format_lazy(
            "If your learners are new to programming and primarily interested "
            "in working with data, Data Carpentry is likely the best choice. "
            "If your learners are interested in learning more about "
            "programming, including version control and automation, Software "
            "Carpentry is likely the best match. If your learners are people "
            "working in library and information related roles interested in "
            "learning data and software skills, Library Carpentry is the best "
            "choice. Please visit the {}, {}, or the {} for more information "
            "about any of our lessons.<br>If you are not sure which workshop "
            "curriculum you would like to have taught, please complete the "
            "<a href='{}'>Workshop Inquiry Form</a>.",
            SWC_LESSONS_LINK,
            DC_LESSONS_LINK,
            LC_LESSONS_LINK,
            INQUIRY_FORM,
        ),
    )
    # Form shows a visible warning here if the selected dates are too soon
    # (3 months)
    preferred_dates = models.DateField(
        blank=True,
        null=True,
        verbose_name="Preferred dates",
        help_text="Please select your preferred first day for the workshop. If you do "
        "not have exact dates or are interested in an alternative schedule, please "
        "indicate so below. Because we need to coordinate with instructors, a minimum "
        "of 2-3 months lead time is required for workshop planning.<br>The preferred "
        "dates are not a guarantee. We do our best to schedule your workshop for the "
        "dates that you have requested, however, a high volume of workshops on a given "
        "date may prevent us from fulfilling your request. Please prepare alternative "
        "dates in the event that we can not accommodate your request.",
    )
    other_preferred_dates = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="If your dates are not set, please provide more information below",
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        verbose_name="What is the preferred language of communication for the workshop?",
        help_text="Our workshops are offered primarily in English, with a few "
        "of our lessons available in Spanish. While materials are "
        "mainly in English, we know it can be valuable to have an "
        "instructor who speaks the native language of the learners. "
        "We will attempt to locate Instructors speaking a particular"
        " language, but cannot guarantee the availability of "
        "non-English speaking Instructors.",
    )
    ATTENDEES_NUMBER_CHOICES = (
        ("10-40", "10-40 (one room, two instructors)"),
        ("40-80", "40-80 (two rooms, four instructors)"),
        ("80-120", "80-120 (three rooms, six instructors)"),
    )

    # MISSING
    # This field is no longer needed, and should be hidden in the form and
    # templates.
    domains = models.ManyToManyField(
        KnowledgeDomain,
        blank=False,
        verbose_name="Domains or topic of interest for target audience",
        help_text="The attendees' academic field(s) of study, if known.",
    )
    # MISSING
    # This field is no longer needed, and should be hidden in the form and
    # templates.
    domains_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        default="",
        verbose_name="Other domains",
    )
    # MISSING
    # This field is no longer needed, and should be hidden in the form and
    # templates.
    academic_levels = models.ManyToManyField(
        AcademicLevel,
        verbose_name="Attendees' academic level / career stage",
        help_text="If you know the academic level(s) of your attendees, indicate them here.",
    )
    # MISSING
    # This field is no longer needed, and should be hidden in the form and
    # templates.
    computing_levels = models.ManyToManyField(
        ComputingExperienceLevel,
        verbose_name="Attendees' level of computing experience",
        help_text="Indicate the attendees' level of computing experience, if "
        "known. We will ask attendees to fill in a skills survey "
        "before the workshop, so this answer can be an "
        "approximation.",
    )
    audience_description = models.TextField(
        verbose_name="Please describe your anticipated audience, including their experience, background, and goals",
    )
    FEE_CHOICES = (
        (
            "nonprofit",
            "I am with a government site, university, or other nonprofit. "
            "I understand the workshop fee as listed on The Carpentries website "
            "and agree to follow through on The Carpentries invoicing process.",
        ),
        (
            "forprofit",
            "I am with a corporate or for-profit site. I understand the costs for "
            "for-profit organisations are higher than the price for not-for-profit "
            "organisations, as listed on The Carpentries website.",
        ),
        (
            "member",
            "I am with a Member organisation so the workshop fee does not apply "
            "(instructor travel costs will still apply for in-person workshops).",
        ),
        (
            "waiver",
            "I am requesting financial support for the workshop fee (instructor "
            "travel costs will still apply for in-person workshops)",
        ),
    )
    administrative_fee = models.CharField(
        max_length=20,
        choices=FEE_CHOICES,
        blank=False,
        null=False,
        default=None,
        verbose_name="Which of the following applies to your payment for the administrative fee?",
        help_text=(
            "<b><a href='{}' target='_blank' rel='noreferrer nofollow'>"
            "The Carpentries website workshop fee listing.</a></b>".format(FEE_DETAILS_URL)
        ),
    )
    scholarship_circumstances = models.TextField(
        blank=True,
        verbose_name="We have a limited number of scholarships available. "
        "Please explain the circumstances for your scholarship "
        "request and let us know what budget you have towards "
        "The Carpentries workshop fees.",
        help_text="Required only if you request a scholarship.",
    )
    TRAVEL_EXPENCES_MANAGEMENT_CHOICES = (
        (
            "booked",
            "Hotel and airfare will be booked by site; ground travel "
            "and meals/incidentals will be reimbursed within 60 days.",
        ),
        (
            "reimbursed",
            "All expenses will be booked by instructors and reimbursed within 60 days.",
        ),
        ("other", "Other:"),
    )
    travel_expences_management = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        default="",
        choices=TRAVEL_EXPENCES_MANAGEMENT_CHOICES,
        verbose_name="How will you manage travel expenses for Carpentries Instructors?",
    )
    travel_expences_management_other = models.CharField(
        max_length=STR_LONGEST,
        null=False,
        blank=True,
        default="",
        verbose_name="Other travel expences management",
    )
    travel_expences_agreement = models.BooleanField(
        null=False,
        blank=False,
        default=False,
        verbose_name="Regardless of the fee due to The Carpentries, I "
        "understand I am also responsible for travel costs for "
        "the Instructors which can include airfare, ground "
        "travel, hotel, and meals/incidentals. I understand "
        "local Instructors will be prioritized but not "
        "guaranteed. Instructor travel costs are managed "
        "directly between the host site and the Instructors, not "
        "through The Carpentries. I will share detailed "
        "information regarding policies and procedures for "
        "travel arrangements with instructors. All "
        "reimbursements will be completed within 60 days of "
        "the workshop.",
    )
    RESTRICTION_CHOICES = (
        ("no_restrictions", "No restrictions"),
        ("other", "Other:"),
    )
    institution_restrictions = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        default="",
        choices=RESTRICTION_CHOICES,
        verbose_name="Our instructors live, teach, and travel globally. We "
        "understand that institutions may have citizenship, "
        "confindentiality agreements or other requirements for "
        "employees or volunteers who facilitate workshops. If "
        "your institution fits this description, please share "
        "your requirements or note that there are no "
        "restrictions.",
    )
    institution_restrictions_other = models.CharField(
        max_length=STR_LONGEST,
        null=False,
        blank=True,
        default="",
        verbose_name="Other (institution restrictions)",
    )
    carpentries_info_source = models.ManyToManyField(
        InfoSource,
        blank=True,
        verbose_name="How did you hear about The Carpentries?",
        help_text="Check all that apply.",
    )
    carpentries_info_source_other = models.CharField(
        max_length=STR_LONGEST,
        null=False,
        blank=True,
        default="",
        verbose_name="Other source for information about The Carpentries",
    )
    user_notes = models.TextField(
        blank=True,
        verbose_name="Will this workshop be conducted in-person or online? "
        "Is there any other information you would like to share "
        "with us?",
        help_text="Knowing if this workshop is on-line or in-person will "
        "help ensure we can best support you in coordinating the event.",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return ("Workshop request ({institution}, {personal} {family}) - {state}").format(
            institution=str(self.institution or self.institution_other_name),
            personal=self.personal,
            family=self.family,
            state=self.get_state_display(),
        )

    def dates(self) -> str:
        if self.preferred_dates:
            return "{:%Y-%m-%d}".format(self.preferred_dates)
        else:
            return self.other_preferred_dates

    def preferred_dates_too_soon(self) -> bool:
        # set cutoff date at 3 months
        cutoff = datetime.timedelta(days=3 * 30)
        if self.preferred_dates:
            return (self.preferred_dates - self.created_at.date()) < cutoff
        return False

    def get_absolute_url(self) -> str:
        return reverse("workshoprequest_details", args=[self.id])
