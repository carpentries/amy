import datetime

from django.db import models, transaction
from django.urls import reverse
from django_countries.fields import CountryField

from workshops.mixins import (
    AssignmentMixin,
    CreatedUpdatedMixin,
    COCAgreementMixin,
    DataPrivacyAgreementMixin,
    EventLinkMixin,
    HostResponsibilitiesMixin,
    StateMixin,
    InstructorAvailabilityMixin,
)
from workshops.models import (
    STR_MED,
    STR_LONG,
    STR_LONGEST,
    Language,
    KnowledgeDomain,
    AcademicLevel,
    ComputingExperienceLevel,
    Curriculum,
    InfoSource,
    CommonRequest,
)


class DataAnalysisLevel(models.Model):
    # ComputingExperienceLevel's sibling
    name = models.CharField(max_length=STR_LONGEST, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = "workshops_dataanalysislevel"


class DCWorkshopTopic(models.Model):
    """Single lesson topic used in a workshop."""

    name = models.CharField(max_length=STR_LONGEST, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = "workshops_dcworkshoptopic"


class DCWorkshopDomain(models.Model):
    """Single domain used in a workshop (it corresponds to a set of lessons
    Data Carpentry prepared)."""

    name = models.CharField(max_length=STR_LONGEST, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = "workshops_dcworkshopdomain"


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


class EventRequest(
    AssignmentMixin, StateMixin, CreatedUpdatedMixin, EventLinkMixin, models.Model
):
    name = models.CharField(max_length=STR_MED)
    email = models.EmailField()
    affiliation = models.CharField(
        max_length=STR_LONG, help_text="University or Company"
    )
    location = models.CharField(
        max_length=STR_LONG, help_text="City, Province, or State"
    )
    country = CountryField()
    conference = models.CharField(
        max_length=STR_LONG,
        verbose_name="If the workshop is to be associated with a conference "
        "or meeting, which one? ",
        blank=True,
        default="",
    )
    preferred_date = models.CharField(
        max_length=STR_LONGEST,
        help_text="Please indicate when you would like to run the workshop. "
        "A range of at least a month is most helpful, although if "
        "you have specific dates you need the workshop, we will try "
        "to accommodate those requests.",
        verbose_name="Preferred workshop dates",
    )
    language = models.ForeignKey(
        Language,
        verbose_name="What human language do you want the workshop to be run" " in?",
        null=True,
        on_delete=models.SET_NULL,
    )

    WORKSHOP_TYPE_CHOICES = (
        ("swc", "Software-Carpentry"),
        ("dc", "Data-Carpentry"),
    )
    workshop_type = models.CharField(
        max_length=STR_MED, choices=WORKSHOP_TYPE_CHOICES, blank=False, default="swc",
    )

    ATTENDEES_NUMBER_CHOICES = (
        ("1-20", "1-20 (one room, two instructors)"),
        ("20-40", "20-40 (one room, two instructors)"),
        ("40-80", "40-80 (two rooms, four instructors)"),
        ("80-120", "80-120 (three rooms, six instructors)"),
    )
    approx_attendees = models.CharField(
        max_length=STR_MED,
        choices=ATTENDEES_NUMBER_CHOICES,
        help_text="This number doesn't need to be precise, but will help us "
        "decide how many instructors your workshop will need."
        "Each workshop must have at least two instructors.",
        verbose_name="Approximate number of Attendees",
        blank=False,
        default="20-40",
    )

    attendee_domains = models.ManyToManyField(
        KnowledgeDomain,
        help_text="The attendees' academic field(s) of study, if known.",
        verbose_name="Domains or topic of interest for target audience",
        blank=False,
    )
    attendee_domains_other = models.CharField(
        max_length=STR_LONG,
        help_text="If none of the fields above works for you.",
        verbose_name="Other domains or topics of interest",
        blank=True,
        default="",
    )
    DATA_TYPES_CHOICES = (
        ("survey", "Survey data (ecology, biodiversity, social science)"),
        ("genomic", "Genomic data"),
        ("geospatial", "Geospatial data"),
        ("text-mining", "Text mining"),
        ("", "Other:"),
    )
    data_types = models.CharField(
        max_length=STR_MED,
        choices=DATA_TYPES_CHOICES,
        verbose_name="We currently have developed or are developing workshops"
        " focused on four types of data. Please let us know which"
        " workshop would best suit your needs.",
        blank=True,
    )
    data_types_other = models.CharField(
        max_length=STR_LONG,
        verbose_name="Other data domains for the workshop",
        blank=True,
    )
    attendee_academic_levels = models.ManyToManyField(
        "workshops.AcademicLevel",
        help_text="If you know the academic level(s) of your attendees, "
        "indicate them here.",
        verbose_name="Attendees' Academic Level",
    )
    attendee_computing_levels = models.ManyToManyField(
        "workshops.ComputingExperienceLevel",
        help_text="Indicate the attendees' level of computing experience, if "
        "known. We will ask attendees to fill in a skills survey "
        "before the workshop, so this answer can be an "
        "approximation.",
        verbose_name="Attendees' level of computing experience",
    )
    attendee_data_analysis_level = models.ManyToManyField(
        DataAnalysisLevel,
        help_text="If you know, indicate learner's general level of data "
        "analysis experience",
        verbose_name="Level of data analysis experience",
    )
    understand_admin_fee = models.BooleanField(
        default=False,
        # verbose_name a.k.a. label and help_text were moved to the
        # SWCEventRequestForm and DCEventRequestForm
    )

    ADMIN_FEE_PAYMENT_CHOICES = (
        ("NP1", "Non-profit / non-partner: US$2500"),
        ("FP1", "For-profit: US$10,000"),
        (
            "self-organized",
            "Self-organized: no fee (please let us know if you "
            "wish to make a donation)",
        ),
        ("waiver", "Waiver requested (please give details in " '"Anything else")'),
    )
    admin_fee_payment = models.CharField(
        max_length=STR_MED,
        choices=ADMIN_FEE_PAYMENT_CHOICES,
        verbose_name="Which of the following applies to your payment for the "
        "administrative fee?",
        blank=False,
        default="NP1",
    )
    fee_waiver_request = models.BooleanField(
        help_text="Waiver's of the administrative fee are available on "
        "a needs basis. If you are interested in submitting a waiver"
        " application please indicate here.",
        verbose_name="I would like to submit an administrative fee waiver "
        "application",
        default=False,
    )
    cover_travel_accomodation = models.BooleanField(
        default=False,
        verbose_name="My institution will cover instructors' travel and "
        "accommodation costs.",
    )
    TRAVEL_REIMBURSEMENT_CHOICES = (
        ("", "Don't know yet."),
        ("book", "Book travel through our university or program."),
        ("reimburse", "Book their own travel and be reimbursed."),
        ("", "Other:"),
    )
    travel_reimbursement = models.CharField(
        max_length=STR_MED,
        verbose_name="How will instructors' travel and accommodations be " "managed?",
        choices=TRAVEL_REIMBURSEMENT_CHOICES,
        blank=True,
        default="",
    )
    travel_reimbursement_other = models.CharField(
        max_length=STR_LONG,
        verbose_name="Other propositions for managing instructors' travel and"
        " accommodations",
        blank=True,
    )
    comment = models.TextField(
        help_text="What else do you want us to know about your workshop? About"
        " your attendees? About you?",
        verbose_name="Anything else?",
        blank=True,
    )

    def get_absolute_url(self):
        return reverse("eventrequest_details", args=[self.pk])

    def __str__(self):
        return "{name} (from {affiliation}, {type} workshop)".format(
            name=self.name, affiliation=self.affiliation, type=self.workshop_type,
        )

    class Meta:
        ordering = ["created_at"]

        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = "workshops_eventrequest"


class EventSubmission(
    AssignmentMixin, StateMixin, CreatedUpdatedMixin, EventLinkMixin, models.Model
):
    url = models.URLField(
        null=False, blank=False, verbose_name="Link to the workshop's website"
    )
    contact_name = models.CharField(
        null=False, blank=False, max_length=STR_LONG, verbose_name="Your name"
    )
    contact_email = models.EmailField(
        null=False,
        blank=False,
        verbose_name="Your email",
        help_text="We may need to contact you regarding workshop details.",
    )
    self_organized = models.BooleanField(
        null=False, default=False, verbose_name="Was the workshop self-organized?"
    )
    notes = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return "Event submission <{}>".format(self.url)

    def get_absolute_url(self):
        return reverse("eventsubmission_details", args=[self.pk])

    class Meta:
        ordering = ["created_at"]

        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = "workshops_eventsubmission"


class DCSelfOrganizedEventRequest(
    AssignmentMixin, StateMixin, CreatedUpdatedMixin, EventLinkMixin, models.Model
):
    """Should someone want to run a self-organized Data Carpentry event, they
    have to fill this specific form first. See
    https://github.com/swcarpentry/amy/issues/761"""

    name = models.CharField(max_length=STR_LONGEST,)
    email = models.EmailField()
    organization = models.CharField(
        max_length=STR_LONGEST, verbose_name="University or organization affiliation",
    )
    INSTRUCTOR_CHOICES = [
        ("", "None"),
        (
            "incomplete",
            "Have gone through instructor training, but haven't "
            "yet completed checkout",
        ),
        ("dc", "Certified Data Carpentry instructor"),
        ("swc", "Certified Software Carpentry instructor"),
        ("both", "Certified Software and Data Carpentry instructor"),
    ]
    instructor_status = models.CharField(
        max_length=STR_MED,
        choices=INSTRUCTOR_CHOICES,
        verbose_name="Your Software and Data Carpentry instructor status",
        blank=True,
    )
    PARTNER_CHOICES = [
        ("y", "Yes"),
        ("n", "No"),
        ("u", "Unsure"),
        ("", "Other (enter below)"),
    ]
    is_partner = models.CharField(
        max_length=1,
        choices=PARTNER_CHOICES,
        blank=True,
        verbose_name="Is your organization a Data Carpentry or Software "
        "Carpentry Partner",
    )
    is_partner_other = models.CharField(
        max_length=STR_LONG,
        default="",
        blank=True,
        verbose_name="Other (is your organization a Partner?)",
    )
    location = models.CharField(
        max_length=STR_LONGEST,
        verbose_name="Location",
        help_text="City, Province or State",
    )
    country = CountryField()
    associated_conference = models.CharField(
        max_length=STR_LONG,
        default="",
        blank=True,
        verbose_name="Associated conference",
        help_text="If the workshop is to be associated with a conference or "
        "meeting, which one?",
    )
    dates = models.CharField(
        max_length=STR_LONGEST,
        verbose_name="Planned workshop dates",
        help_text="Preferably in YYYY-MM-DD to YYYY-MM-DD format",
    )

    # workshop domain(s)
    domains = models.ManyToManyField(
        DCWorkshopDomain,
        blank=False,
        verbose_name="Domain for the workshop",
        help_text="Set of lessons you're going to teach",
    )
    domains_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        default="",
        verbose_name="Other domains for the workshop",
        help_text="If none of the fields above works for you.",
    )

    # Lesson topics to be taught during the workshop
    topics = models.ManyToManyField(
        DCWorkshopTopic,
        blank=False,
        verbose_name="Topics to be taught",
        help_text="A Data Carpentry workshop must include a Data Carpentry "
        "lesson on data organization and three other modules in the "
        "same domain from the Data Carpentry curriculum (see <a "
        'href="http://www.datacarpentry.org/workshops/">http://www.'
        "datacarpentry.org/workshops/</a>). If you do want to "
        "include materials not in our curriculum, please note that "
        "below and we'll get in touch.",
    )
    topics_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True,
        default="",
        verbose_name="Other topics to be taught",
        help_text="If none of the fields above works for you.",
    )

    # questions about attendees' experience levels
    attendee_academic_levels = models.ManyToManyField(
        "workshops.AcademicLevel",
        help_text="If you know the academic level(s) of your attendees, "
        "indicate them here.",
        verbose_name="Attendees' academic level",
    )
    attendee_data_analysis_level = models.ManyToManyField(
        DataAnalysisLevel,
        help_text="If you know, indicate learner's general level of data "
        "analysis experience",
        verbose_name="Attendees' level of data analysis experience",
    )

    # payments
    PAYMENT_CHOICES = [
        (
            "per_participant",
            "I will contribute $25/participant through " "registration fees",
        ),
        ("invoice", "I will contribute $500 via an invoice"),
        ("credit_card", "I will contribute $500 via a credit card payment"),
        ("fee_waiver", "I would like to request a fee waiver"),
    ]
    payment = models.CharField(
        max_length=STR_MED,
        blank=False,
        choices=PAYMENT_CHOICES,
        default="per_participant",
        verbose_name="Payment choice",
        help_text="Self-organized workshops for non-Partner organizations are "
        "$500 or $25/participant for a workshop licensing fee (<a "
        'href="http://www.datacarpentry.org/self-organized-workshops'
        '/">http://www.datacarpentry.org/self-organized-workshops/'
        "</a>). Fee waivers are available and generally granted upon"
        " request.",
    )
    fee_waiver_reason = models.CharField(
        max_length=STR_LONGEST,
        default="",
        blank=True,
        verbose_name="Reason for requesting a fee waiver",
    )

    # confirmations
    handle_registration = models.BooleanField(
        default=False,
        blank=False,
        verbose_name="I confirm that I will handle registration for this" " workshop",
    )
    distribute_surveys = models.BooleanField(
        default=False,
        blank=False,
        verbose_name="I confirm that I will distribute the Data Carpentry "
        "surveys to workshop participants",
    )
    follow_code_of_conduct = models.BooleanField(
        default=False,
        blank=False,
        verbose_name="I confirm that I will follow the Data Carpentry Code of"
        " Conduct",
    )

    def get_absolute_url(self):
        return reverse("dcselforganizedeventrequest_details", args=[self.pk])

    class Meta:
        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = "workshops_dcselforganizedeventrequest"


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
    country = CountryField(null=False, blank=False, verbose_name="Country",)
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
        max_length=STR_LONGEST, blank=True, default="", verbose_name="Other domains",
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
        + " for more information about any of our lessons. If you’re "
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
    number_attendees = models.CharField(
        max_length=15,
        choices=ATTENDEES_NUMBER_CHOICES,
        blank=True,
        null=True,
        default=None,
        verbose_name="Anticipated number of attendees",
        help_text="This number doesn't need to be precise, but will help us "
        "decide how many instructors your workshop will need. "
        "Each workshop must have at least two instructors.",
    )
    FEE_CHOICES = (
        UNSURE_CHOICE,
        (
            "nonprofit",
            "I am with a government site, university, or other "
            "nonprofit. I understand the workshop fee of US$2500, "
            "and agree to follow through on The Carpentries "
            "invoicing process.",
        ),
        (
            "forprofit",
            "I am with a corporate or for-profit site. I understand "
            "The Carpentries staff will contact me about workshop "
            "fees. I will follow through on The Carpentries "
            "invoicing process for the agreed upon fee.",
        ),
        (
            "member",
            "I am with a Member Organisation so the workshop fee does "
            "not apply (Instructor travel costs will still apply).",
        ),
        (
            "waiver",
            "I am requesting a scholarship for the workshop fee "
            "(Instructor travel costs will still apply).",
        ),
    )
    administrative_fee = models.CharField(
        max_length=20,
        choices=FEE_CHOICES,
        blank=True,
        null=True,
        default=None,
        verbose_name="Which of the following applies to your payment for the "
        "administrative fee?",
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

    workshop_url = models.URLField(
        max_length=STR_LONGEST,
        blank=True,
        null=False,
        default="",
        verbose_name="Please share your workshop URL",
        help_text="Use the link to the website, not the repository. This is "
        "typically in the format <a>https://username.github.io/"
        "YYYY-MM-DD-sitename</a>.  If you are running an online workshop, "
        "please use the format YYYY-MM-DD-sitename-online.",
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
    country = CountryField(null=True, blank=False, verbose_name="Country",)
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
