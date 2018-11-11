from django.db import models
from django.db.models import (
    Q,
)
from django.urls import reverse
from django_countries.fields import CountryField

from workshops.fields import NullableGithubUsernameField
from workshops.models import (
    STR_MED, STR_LONG, STR_LONGEST,
    ActiveMixin,
    AssignmentMixin,
    CreatedUpdatedMixin,
    DataPrivacyAgreementMixin,
    StateMixin,
    EventLink,
    Person,
    TrainingRequest,
    Language,
    KnowledgeDomain,
    Lesson,
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
        db_table = 'workshops_dataanalysislevel'


class DCWorkshopTopic(models.Model):
    """Single lesson topic used in a workshop."""
    name = models.CharField(max_length=STR_LONGEST, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = 'workshops_dcworkshoptopic'


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
        db_table = 'workshops_dcworkshopdomain'


class ProfileUpdateRequest(ActiveMixin, CreatedUpdatedMixin,
                           DataPrivacyAgreementMixin, models.Model):
    personal = models.CharField(
        max_length=STR_LONG,
        verbose_name='Personal (first) name',
        blank=False,
    )
    middle = models.CharField(
        max_length=STR_LONG,
        verbose_name='Middle name',
        blank=True,
    )
    family = models.CharField(
        max_length=STR_LONG,
        verbose_name='Family (last) name',
        blank=False,
    )
    email = models.EmailField(
        verbose_name='Email address',
        blank=False,
    )
    affiliation = models.CharField(
        max_length=STR_LONG,
        help_text='What university, company, lab, or other organization are '
        'you affiliated with (if any)?',
        blank=False,
    )
    country = CountryField(
        null=False, blank=True, default='',
        verbose_name='Country of residence',
    )
    airport_iata = models.CharField(
        max_length=3,
        verbose_name='Nearest major airport',
        help_text='Please use its 3-letter IATA code '
        '(<a href="http://www.airportcodes.aero/" target="_blank">'
        'http://www.airportcodes.aero/</a>) to tell us where you\'re located.',
        blank=False, null=False,
    )

    occupation = models.CharField(
        max_length=STR_MED,
        choices=TrainingRequest.OCCUPATION_CHOICES,
        verbose_name='What is your current occupation/career stage?',
        help_text='Please choose the one that best describes you.',
        null=False, blank=True, default='undisclosed',
    )
    occupation_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other occupation/career stage',
        blank=True, default='',
    )
    github = NullableGithubUsernameField(
        verbose_name='GitHub username',
        help_text='Please put only a single username here.',
        blank=True, default='',
    )
    twitter = models.CharField(
        max_length=STR_LONG,
        verbose_name='Twitter username',
        blank=True, default='',
    )
    orcid = models.CharField(
        max_length=STR_LONG,
        verbose_name='ORCID ID',
        blank=True, default='',
    )
    website = models.CharField(
        max_length=STR_LONG,
        verbose_name='Personal website',
        default='', blank=True,
    )

    GENDER_CHOICES = (
        (Person.UNDISCLOSED, 'Prefer not to say'),
        (Person.FEMALE, 'Female'),
        (Person.MALE, 'Male'),
        (Person.OTHER, 'Other:'),
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        null=False, blank=False, default=Person.UNDISCLOSED,
    )
    gender_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other gender',
        blank=True, default='',
    )
    domains = models.ManyToManyField(
        KnowledgeDomain,
        verbose_name='Areas of expertise',
        help_text='Please check all that apply.',
        limit_choices_to=~Q(name__startswith='Don\'t know yet'),
        blank=True,
    )
    domains_other = models.CharField(
        max_length=STR_LONGEST,
        verbose_name='Other areas of expertise',
        blank=True, default='',
    )
    languages = models.ManyToManyField(
        Language,
        verbose_name='Languages you can teach in',
        blank=True,
    )
    lessons = models.ManyToManyField(
        Lesson,
        verbose_name='Topic and lessons you\'re comfortable teaching',
        help_text='Please mark ALL that apply.',
        blank=False,
    )
    lessons_other = models.CharField(
        max_length=STR_LONGEST,
        verbose_name='Other topics/lessons you\'re comfortable teaching',
        help_text='Please include lesson URLs.',
        blank=True, default='',
    )
    notes = models.TextField(
        default="",
        blank=True)
    may_contact = models.BooleanField(
        default=True,
        help_text='Allow to contact from The Carpentries according to the '
                  '<a href="https://docs.carpentries.org/'
                  'topic_folders/policies/privacy.html" target="_blank">'
                  'Privacy Policy</a>.',
    )
    publish_profile = models.BooleanField(
        default=False,
        verbose_name='Consent to making profile public',
        help_text='Allow to post your name and any public profile you list '
                  '(website, Twitter) on our instructors website. Emails will'
                  ' not be posted.'
    )

    def get_full_name(self):
        middle = ''
        if self.middle:
            middle = ' {0}'.format(self.middle)
        return '{0}{1} {2}'.format(self.personal, middle, self.family)

    def get_short_name(self):
        return self.personal

    def save(self, *args, **kwargs):
        """Save nullable char fields as empty strings."""
        self.personal = self.personal.strip()
        self.family = self.family.strip()
        self.email = self.email.strip()
        self.gender = self.gender or ''
        self.occupation = self.occupation or ''
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('profileupdaterequest_details', args=[self.pk])

    def __str__(self):
        return "{personal} {family} <{email}> (from {affiliation})".format(
            personal=self.personal, family=self.family, email=self.email,
            affiliation=self.affiliation,
        )

    class Meta:
        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = 'workshops_profileupdaterequest'


class EventRequest(AssignmentMixin, StateMixin, CreatedUpdatedMixin,
                   EventLink, models.Model):
    name = models.CharField(max_length=STR_MED)
    email = models.EmailField()
    affiliation = models.CharField(max_length=STR_LONG,
                                   help_text='University or Company')
    location = models.CharField(max_length=STR_LONG,
                                help_text='City, Province, or State')
    country = CountryField()
    conference = models.CharField(
        max_length=STR_LONG,
        verbose_name='If the workshop is to be associated with a conference '
                     'or meeting, which one? ',
        blank=True, default='',
    )
    preferred_date = models.CharField(
        max_length=STR_LONGEST,
        help_text='Please indicate when you would like to run the workshop. '
                  'A range of at least a month is most helpful, although if '
                  'you have specific dates you need the workshop, we will try '
                  'to accommodate those requests.',
        verbose_name='Preferred workshop dates',
    )
    language = models.ForeignKey(
        Language,
        verbose_name='What human language do you want the workshop to be run'
                     ' in?',
        null=True,
        on_delete=models.SET_NULL,
    )

    WORKSHOP_TYPE_CHOICES = (
        ('swc', 'Software-Carpentry'),
        ('dc', 'Data-Carpentry'),
    )
    workshop_type = models.CharField(
        max_length=STR_MED,
        choices=WORKSHOP_TYPE_CHOICES,
        blank=False, default='swc',
    )

    ATTENDEES_NUMBER_CHOICES = (
        ('1-20', '1-20 (one room, two instructors)'),
        ('20-40', '20-40 (one room, two instructors)'),
        ('40-80', '40-80 (two rooms, four instructors)'),
        ('80-120', '80-120 (three rooms, six instructors)'),
    )
    approx_attendees = models.CharField(
        max_length=STR_MED,
        choices=ATTENDEES_NUMBER_CHOICES,
        help_text='This number doesn\'t need to be precise, but will help us '
                  'decide how many instructors your workshop will need.'
                  'Each workshop must have at least two instructors.',
        verbose_name='Approximate number of Attendees',
        blank=False,
        default='20-40',
    )

    attendee_domains = models.ManyToManyField(
        KnowledgeDomain,
        help_text='The attendees\' academic field(s) of study, if known.',
        verbose_name='Domains or topic of interest for target audience',
        blank=False,
    )
    attendee_domains_other = models.CharField(
        max_length=STR_LONG,
        help_text='If none of the fields above works for you.',
        verbose_name='Other domains or topics of interest',
        blank=True, default="",
    )
    DATA_TYPES_CHOICES = (
        ('survey', 'Survey data (ecology, biodiversity, social science)'),
        ('genomic', 'Genomic data'),
        ('geospatial', 'Geospatial data'),
        ('text-mining', 'Text mining'),
        ('', 'Other:'),
    )
    data_types = models.CharField(
        max_length=STR_MED,
        choices=DATA_TYPES_CHOICES,
        verbose_name='We currently have developed or are developing workshops'
                     ' focused on four types of data. Please let us know which'
                     ' workshop would best suit your needs.',
        blank=True,
    )
    data_types_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other data domains for the workshop',
        blank=True,
    )
    attendee_academic_levels = models.ManyToManyField(
        'workshops.AcademicLevel',
        help_text='If you know the academic level(s) of your attendees, '
                  'indicate them here.',
        verbose_name='Attendees\' Academic Level',
    )
    attendee_computing_levels = models.ManyToManyField(
        'workshops.ComputingExperienceLevel',
        help_text='Indicate the attendees\' level of computing experience, if '
                  'known. We will ask attendees to fill in a skills survey '
                  'before the workshop, so this answer can be an '
                  'approximation.',
        verbose_name='Attendees\' level of computing experience',
    )
    attendee_data_analysis_level = models.ManyToManyField(
        DataAnalysisLevel,
        help_text='If you know, indicate learner\'s general level of data '
                  'analysis experience',
        verbose_name='Level of data analysis experience',
    )
    understand_admin_fee = models.BooleanField(
        default=False,
        # verbose_name a.k.a. label and help_text were moved to the
        # SWCEventRequestForm and DCEventRequestForm
    )

    ADMIN_FEE_PAYMENT_CHOICES = (
        ('NP1', 'Non-profit / non-partner: US$2500'),
        ('FP1', 'For-profit: US$10,000'),
        ('self-organized', 'Self-organized: no fee (please let us know if you '
                           'wish to make a donation)'),
        ('waiver', 'Waiver requested (please give details in '
                   '"Anything else")'),
    )
    admin_fee_payment = models.CharField(
        max_length=STR_MED,
        choices=ADMIN_FEE_PAYMENT_CHOICES,
        verbose_name='Which of the following applies to your payment for the '
                     'administrative fee?',
        blank=False,
        default='NP1',
    )
    fee_waiver_request = models.BooleanField(
        help_text='Waiver\'s of the administrative fee are available on '
                  'a needs basis. If you are interested in submitting a waiver'
                  ' application please indicate here.',
        verbose_name='I would like to submit an administrative fee waiver '
                     'application',
        default=False,
    )
    cover_travel_accomodation = models.BooleanField(
        default=False,
        verbose_name='My institution will cover instructors\' travel and '
                     'accommodation costs.',
    )
    TRAVEL_REIMBURSEMENT_CHOICES = (
        ('', 'Don\'t know yet.'),
        ('book', 'Book travel through our university or program.'),
        ('reimburse', 'Book their own travel and be reimbursed.'),
        ('', 'Other:'),
    )
    travel_reimbursement = models.CharField(
        max_length=STR_MED,
        verbose_name='How will instructors\' travel and accommodations be '
                     'managed?',
        choices=TRAVEL_REIMBURSEMENT_CHOICES,
        blank=True, default='',
    )
    travel_reimbursement_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other propositions for managing instructors\' travel and'
                     ' accommodations',
        blank=True,
    )
    comment = models.TextField(
        help_text='What else do you want us to know about your workshop? About'
                  ' your attendees? About you?',
        verbose_name='Anything else?',
        blank=True,
    )

    def get_absolute_url(self):
        return reverse('eventrequest_details', args=[self.pk])

    def __str__(self):
        return "{name} (from {affiliation}, {type} workshop)".format(
            name=self.name, affiliation=self.affiliation,
            type=self.workshop_type,
        )

    class Meta:
        ordering = ['created_at']

        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = 'workshops_eventrequest'


class EventSubmission(AssignmentMixin, StateMixin, CreatedUpdatedMixin,
                      EventLink, models.Model):
    url = models.URLField(
        null=False, blank=False,
        verbose_name='Link to the workshop\'s website')
    contact_name = models.CharField(
        null=False, blank=False, max_length=STR_LONG,
        verbose_name='Your name')
    contact_email = models.EmailField(
        null=False, blank=False,
        verbose_name='Your email',
        help_text='We may need to contact you regarding workshop details.')
    self_organized = models.BooleanField(
        null=False, default=False,
        verbose_name='Was the workshop self-organized?')
    notes = models.TextField(
        null=False, blank=True, default='')

    def __str__(self):
        return 'Event submission <{}>'.format(self.url)

    def get_absolute_url(self):
        return reverse('eventsubmission_details', args=[self.pk])

    class Meta:
        ordering = ['created_at']

        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = 'workshops_eventsubmission'


class DCSelfOrganizedEventRequest(AssignmentMixin, StateMixin,
                                  CreatedUpdatedMixin, EventLink,
                                  models.Model):
    """Should someone want to run a self-organized Data Carpentry event, they
    have to fill this specific form first. See
    https://github.com/swcarpentry/amy/issues/761"""

    name = models.CharField(
        max_length=STR_LONGEST,
    )
    email = models.EmailField()
    organization = models.CharField(
        max_length=STR_LONGEST,
        verbose_name='University or organization affiliation',
    )
    INSTRUCTOR_CHOICES = [
        ('', 'None'),
        ('incomplete', 'Have gone through instructor training, but haven\'t '
                       'yet completed checkout'),
        ('dc', 'Certified Data Carpentry instructor'),
        ('swc', 'Certified Software Carpentry instructor'),
        ('both', 'Certified Software and Data Carpentry instructor'),
    ]
    instructor_status = models.CharField(
        max_length=STR_MED, choices=INSTRUCTOR_CHOICES,
        verbose_name='Your Software and Data Carpentry instructor status',
        blank=True,
    )
    PARTNER_CHOICES = [
        ('y', 'Yes'),
        ('n', 'No'),
        ('u', 'Unsure'),
        ('', 'Other (enter below)'),
    ]
    is_partner = models.CharField(
        max_length=1,
        choices=PARTNER_CHOICES,
        blank=True,
        verbose_name='Is your organization a Data Carpentry or Software '
                     'Carpentry Partner'
    )
    is_partner_other = models.CharField(
        max_length=STR_LONG,
        default='', blank=True,
        verbose_name='Other (is your organization a Partner?)',
    )
    location = models.CharField(
        max_length=STR_LONGEST,
        verbose_name='Location',
        help_text='City, Province or State',
    )
    country = CountryField()
    associated_conference = models.CharField(
        max_length=STR_LONG,
        default='', blank=True,
        verbose_name='Associated conference',
        help_text='If the workshop is to be associated with a conference or '
                  'meeting, which one?',
    )
    dates = models.CharField(
        max_length=STR_LONGEST,
        verbose_name='Planned workshop dates',
        help_text='Preferably in YYYY-MM-DD to YYYY-MM-DD format',
    )

    # workshop domain(s)
    domains = models.ManyToManyField(
        DCWorkshopDomain,
        blank=False,
        verbose_name='Domain for the workshop',
        help_text='Set of lessons you\'re going to teach',
    )
    domains_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True, default='',
        verbose_name='Other domains for the workshop',
        help_text='If none of the fields above works for you.',
    )

    # Lesson topics to be taught during the workshop
    topics = models.ManyToManyField(
        DCWorkshopTopic,
        blank=False,
        verbose_name='Topics to be taught',
        help_text='A Data Carpentry workshop must include a Data Carpentry '
                  'lesson on data organization and three other modules in the '
                  'same domain from the Data Carpentry curriculum (see <a '
                  'href="http://www.datacarpentry.org/workshops/">http://www.'
                  'datacarpentry.org/workshops/</a>). If you do want to '
                  'include materials not in our curriculum, please note that '
                  'below and we\'ll get in touch.'
    )
    topics_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True, default='',
        verbose_name='Other topics to be taught',
        help_text='If none of the fields above works for you.',
    )

    # questions about attendees' experience levels
    attendee_academic_levels = models.ManyToManyField(
        'workshops.AcademicLevel',
        help_text='If you know the academic level(s) of your attendees, '
                  'indicate them here.',
        verbose_name='Attendees\' academic level',
    )
    attendee_data_analysis_level = models.ManyToManyField(
        DataAnalysisLevel,
        help_text='If you know, indicate learner\'s general level of data '
                  'analysis experience',
        verbose_name='Attendees\' level of data analysis experience',
    )

    # payments
    PAYMENT_CHOICES = [
        ('per_participant', 'I will contribute $25/participant through '
                            'registration fees'),
        ('invoice', 'I will contribute $500 via an invoice'),
        ('credit_card', 'I will contribute $500 via a credit card payment'),
        ('fee_waiver', 'I would like to request a fee waiver'),
    ]
    payment = models.CharField(
        max_length=STR_MED,
        blank=False, choices=PAYMENT_CHOICES,
        default='per_participant',
        verbose_name='Payment choice',
        help_text='Self-organized workshops for non-Partner organizations are '
                  '$500 or $25/participant for a workshop licensing fee (<a '
                  'href="http://www.datacarpentry.org/self-organized-workshops'
                  '/">http://www.datacarpentry.org/self-organized-workshops/'
                  '</a>). Fee waivers are available and generally granted upon'
                  ' request.',
    )
    fee_waiver_reason = models.CharField(
        max_length=STR_LONGEST,
        default='', blank=True,
        verbose_name='Reason for requesting a fee waiver',
    )

    # confirmations
    handle_registration = models.BooleanField(
        default=False, blank=False,
        verbose_name='I confirm that I will handle registration for this'
                     ' workshop',
    )
    distribute_surveys = models.BooleanField(
        default=False, blank=False,
        verbose_name='I confirm that I will distribute the Data Carpentry '
                     'surveys to workshop participants',
    )
    follow_code_of_conduct = models.BooleanField(
        default=False, blank=False,
        verbose_name='I confirm that I will follow the Data Carpentry Code of'
                     ' Conduct',
    )

    def get_absolute_url(self):
        return reverse('dcselforganizedeventrequest_details', args=[self.pk])

    class Meta:
        # This model was imported from Workshops application, but for
        # compatibility reasons (we don't want to rename DB table, as it
        # doesn't work in SQLite) we're keeping it under the same name in DB.
        db_table = 'workshops_dcselforganizedeventrequest'
