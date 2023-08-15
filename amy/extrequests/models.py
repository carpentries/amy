import datetime

from django.db import models, transaction
from django.urls import reverse
from django_countries.fields import CountryField

from workshops.consts import FEE_DETAILS_URL
from workshops.mixins import (
    AssignmentMixin,
    COCAgreementMixin,
    CreatedUpdatedMixin,
    DataPrivacyAgreementMixin,
    EventLinkMixin,
    HostResponsibilitiesMixin,
    InstructorAvailabilityMixin,
    StateMixin,
)
from workshops.models import (
    STR_LONGEST,
    AcademicLevel,
    CommonRequest,
    ComputingExperienceLevel,
    Curriculum,
    InfoSource,
    KnowledgeDomain,
    Language,
)


class DataVariant(models.Model):
    name = models.CharField(
        max_length=300,
        null=False,
        blank=False,
        default="",
        unique=True,
        verbose_name="Name",
        help_text="Data variant name and description",
    )
    unknown = models.BooleanField(
        null=False,
        blank=True,
        default=False,
        verbose_name="Unknown entry",
        help_text="Mark this record as 'I don't know yet', or "
        "'Unknown', or 'Not sure yet'. There can be only one such "
        "record in the database.",
    )

    class Meta:
        verbose_name = "Data variant"
        verbose_name_plural = "Data variants"
        ordering = [
            "id",
        ]

    def __str__(self):
        return self.name

    @transaction.atomic
    def save(self, *args, **kwargs):
        """When saving with `unknown=True`, update all other records with this
        parameter to `unknown=False`. This helps keeping only one record with
        `unknown=True` in the database - a specific case of uniqueness."""

        # wrapped in transaction in order to prevent from updating records to
        # `unknown=False` when saving fails
        if self.unknown:
            DataVariant.objects.filter(unknown=True).update(unknown=False)
        return super().save(*args, **kwargs)


class WorkshopInquiryRequest(
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
    """
    This model is used for storing inquiry information from anyone interested
    in The Carpentries and workshops in general.
    """

    UNSURE_CHOICE = ("", "Not sure yet.")

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
    # Here starts "Your Audience" part with this description:
    # The Carpentries offers several different workshops intended for audiences
    # from different domain backgrounds, with different computational
    # experience and learning goals. Your responses to the following questions
    # will help us advise you on which workshop(s) may best serve your
    # audience. All questions are optional so please share as much as you can.
    routine_data = models.ManyToManyField(
        DataVariant,
        blank=True,
        verbose_name="What kinds of data does your target audience routinely "
        "work with?",
        help_text="Check all that apply.",
    )
    routine_data_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        default="",
        verbose_name="Other kinds of routinely worked-with data",
    )
    domains = models.ManyToManyField(
        KnowledgeDomain,
        blank=True,
        verbose_name="Domains or topic of interest for target audience",
        help_text="The attendees' academic field(s) of study, if known. Check "
        "all that apply.",
    )
    domains_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        default="",
        verbose_name="Other domains",
    )
    academic_levels = models.ManyToManyField(
        AcademicLevel,
        blank=True,
        verbose_name="Attendees' academic level / career stage",
        help_text="If you know the academic level(s) of your attendees, "
        "indicate them here. Check all that apply.",
    )
    computing_levels = models.ManyToManyField(
        ComputingExperienceLevel,
        blank=True,
        verbose_name="Attendees' level of computing experience",
        help_text="Indicate the attendees' level of computing experience, if "
        "known. We will ask attendees to fill in a skills survey "
        "before the workshop, so this answer can be an "
        "approximation. Check all that apply.",
    )
    audience_description = models.TextField(
        blank=True,
        verbose_name="Please describe your anticipated audience, including "
        "their experience, background, and goals",
    )
    SWC_LESSONS_LINK = (
        '<a href="https://software-carpentry.org/lessons/">'
        "Software Carpentry lessons page</a>"
    )
    DC_LESSONS_LINK = (
        '<a href="http://www.datacarpentry.org/lessons/">'
        "Data Carpentry lessons page</a>"
    )
    LC_LESSONS_LINK = (
        '<a href="https://librarycarpentry.org/lessons/">'
        "Library Carpentry lessons page</a>"
    )
    requested_workshop_types = models.ManyToManyField(
        Curriculum,
        limit_choices_to={"active": True},
        blank=True,
        verbose_name="Which Carpentries workshop are you requesting?",
        help_text="If your learners are new to programming and primarily "
        "interested in working with data, Data Carpentry is likely "
        "the best choice. If your learners are interested in "
        "learning more about programming, including version control"
        " and automation, Software Carpentry is likely the best "
        "match. If your learners are people working in library and "
        "information related roles interested in learning data and "
        "software skills, Library Carpentry is the best choice. "
        "Please visit the "
        + SWC_LESSONS_LINK
        + ", "
        + DC_LESSONS_LINK
        + ", or the "
        + LC_LESSONS_LINK
        + " for more information about any of our lessons. If you're "
        "not sure and would like to discuss with us, please select "
        'the "Don\'t know yet" option below.<br class="mb-1">'
        "Check all that apply.",
    )
    preferred_dates = models.DateField(
        blank=True,
        null=True,
        verbose_name="Preferred dates",
        help_text="Our workshops typically run two full days. Please select "
        "your preferred first day for the workshop. If you do not "
        "have exact dates or are interested in an alternative "
        "schedule, please indicate so below. Because we need to "
        "coordinate with instructors, a minimum of 2-3 months lead "
        "time is required for workshop planning.",
    )
    other_preferred_dates = models.CharField(
        max_length=200,
        blank=True,
        null=False,
        default="",
        verbose_name="If your dates are not set, please provide more "
        "information below",
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name="What is the preferred language of communication for the "
        "workshop?",
        help_text="Our workshops are offered primarily in English, with a few "
        "of our lessons available in Spanish. While materials are "
        "mainly in English, we know it can be valuable to have an "
        "instructor who speaks the native language of the learners. "
        "We will attempt to locate Instructors speaking a particular"
        " language, but cannot guarantee the availability of "
        "non-English speaking Instructors.",
    )
    ATTENDEES_NUMBER_CHOICES = (
        UNSURE_CHOICE,
        ("10-40", "10-40 (one room, two instructors)"),
        ("40-80", "40-80 (two rooms, four instructors)"),
        ("80-120", "80-120 (three rooms, six instructors)"),
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
            "for-profit organisations are four times the price for not-for-profit "
            "organisations.",
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
        verbose_name="Which of the following applies to your payment for the "
        "administrative fee?",
        help_text=(
            "<a href='{}' target='_blank' rel='noreferrer nofollow'>"
            "The Carpentries website workshop fee listing.</a>".format(FEE_DETAILS_URL)
        ),
    )
    TRAVEL_EXPENCES_MANAGEMENT_CHOICES = (
        UNSURE_CHOICE,
        (
            "booked",
            "Hotel and airfare will be booked by site; ground travel "
            "and meals/incidentals will be reimbursed within 60 days.",
        ),
        (
            "reimbursed",
            "All expenses will be booked by instructors and "
            "reimbursed within 60 days.",
        ),
        ("other", "Other:"),
    )
    travel_expences_management = models.CharField(
        max_length=20,
        null=False,
        blank=True,
        default="",
        choices=TRAVEL_EXPENCES_MANAGEMENT_CHOICES,
        verbose_name="How will you manage travel expenses for Carpentries "
        "Instructors?",
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
        UNSURE_CHOICE,
        ("no_restrictions", "No restrictions."),
        ("other", "Other:"),
    )
    institution_restrictions = models.CharField(
        max_length=20,
        null=False,
        blank=True,
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

    # override field `public_event` from CommonRequest mixin
    public_event = models.CharField(
        max_length=CommonRequest._meta.get_field("public_event").max_length,
        null=False,
        blank=True,
        default="",
        choices=(UNSURE_CHOICE,)
        + CommonRequest._meta.get_field("public_event").choices,
        verbose_name=CommonRequest._meta.get_field("public_event").verbose_name,
        help_text=CommonRequest._meta.get_field("public_event").help_text,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return (
            "Workshop inquiry ({institution}, {personal} {family}) - {state}"
        ).format(
            institution=str(self.institution or self.institution_other_name),
            personal=self.personal,
            family=self.family,
            state=self.get_state_display(),
        )

    def dates(self):
        if self.preferred_dates:
            return "{:%Y-%m-%d}".format(self.preferred_dates)
        else:
            return self.other_preferred_dates

    def preferred_dates_too_soon(self):
        # set cutoff date at 2 months
        cutoff = datetime.timedelta(days=2 * 30)
        if self.preferred_dates:
            return (self.preferred_dates - self.created_at.date()) < cutoff
        return False

    def get_absolute_url(self):
        return reverse("workshopinquiry_details", args=[self.id])


class SelfOrganisedSubmission(
    AssignmentMixin,
    StateMixin,
    CreatedUpdatedMixin,
    CommonRequest,
    DataPrivacyAgreementMixin,
    COCAgreementMixin,
    HostResponsibilitiesMixin,
    EventLinkMixin,
    models.Model,
):
    """
    This model is used for storing user-submitted self-organised workshop
    information. It's very similar to Workshop Submission combined with
    DC Self-Organized Workshop Request.
    """

    start = models.DateField(
        null=True,
        verbose_name="Workshop start date",
        help_text="Please provide the dates that your Self-Organised workshop will"
        " run.",
    )
    end = models.DateField(null=True, verbose_name="Workshop end date")
    workshop_url = models.URLField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="Please share your workshop URL",
        help_text="Please share the link to the public-facing workshop website. If you "
        "are using our template, this is typically in the format of https://username."
        "github.io/YYYY-MM-DD-sitename or https://username.github.io/"
        "YYYY-MM-DD-sitename-online. We do not need links to a separate registration "
        "page, GitHub repo, or any other related pages.",
    )
    FORMAT_CHOICES = (
        ("standard", "Standard two-day Carpentries workshop"),
        ("short", "Short session (less than two days)"),
        (
            "periodic",
            "Modules taught over a period of time (several weeks, "
            "one semester, etc.)",
        ),
        ("other", "Other:"),
    )
    workshop_format = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        default="",
        choices=FORMAT_CHOICES,
        verbose_name="What is the format of this workshop?",
    )
    workshop_format_other = models.CharField(
        max_length=STR_LONGEST,
        null=False,
        blank=True,
        default="",
        verbose_name="Other workshop format",
    )
    workshop_types = models.ManyToManyField(
        Curriculum,
        limit_choices_to={"active": True},
        blank=False,
        verbose_name="Which Carpentries workshop are you teaching?",
    )
    workshop_types_other = models.CharField(
        max_length=STR_LONGEST,
        null=False,
        blank=True,
        default="",
        verbose_name="Other workshop types",
    )
    workshop_types_other_explain = models.TextField(
        blank=True,
        verbose_name='If you selected "Mix & Match", please provide more'
        " information here",
        help_text="For example \"We are teaching Software Carpentry's Git "
        'lesson only" or "We are teaching Data Carpentry\'s Ecology '
        'workshop, but not teaching a programming language."',
    )
    country = CountryField(
        null=True,
        blank=False,
        verbose_name="Country",
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        verbose_name="What language is this workshop being conducted in?",
    )

    class Meta:
        verbose_name = "Self-Organised Submission"
        verbose_name_plural = "Self-Organised Submissions"
        ordering = ["created_at"]

    def __str__(self):
        return (
            "Self-Organised Submission ({institution}, {personal} {family}) - {state}"
        ).format(
            institution=str(self.institution or self.institution_other_name),
            personal=self.personal,
            family=self.family,
            state=self.get_state_display(),
        )

    def get_absolute_url(self):
        return reverse("selforganisedsubmission_details", args=[self.id])
