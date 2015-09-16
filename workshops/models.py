import datetime
import re

from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from django_countries.fields import CountryField
import reversion

#------------------------------------------------------------

STR_SHORT   =  10         # length of short strings
STR_MED     =  40         # length of medium strings
STR_LONG    = 100         # length of long strings
STR_REG_KEY =  20         # length of Eventbrite registration key

#------------------------------------------------------------

class Host(models.Model):
    '''Represent a workshop's host.'''

    domain     = models.CharField(max_length=STR_LONG, unique=True)
    fullname   = models.CharField(max_length=STR_LONG, unique=True)
    country    = CountryField(null=True, blank=True)
    notes      = models.TextField(default="", blank=True)

    def __str__(self):
        return self.domain

    def get_absolute_url(self):
        return reverse('host_details', args=[str(self.domain)])

    class Meta:
        ordering = ('domain', )

#------------------------------------------------------------

class Airport(models.Model):
    '''Represent an airport (used to locate instructors).'''

    iata = models.CharField(max_length=STR_SHORT, unique=True, verbose_name="IATA code",
                            help_text='<a href="https://www.world-airport-codes.com/">Look up code</a>')
    fullname  = models.CharField(max_length=STR_LONG, unique=True, verbose_name="Airport name")
    country   = CountryField()
    latitude  = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return '{0}: {1}'.format(self.iata, self.fullname)

    def get_absolute_url(self):
        return reverse('airport_details', args=[str(self.iata)])

#------------------------------------------------------------

class PersonManager(BaseUserManager):
    """
    Create users and superusers from command line.

    For example:

      $ python manage.py createsuperuser
    """

    def create_user(self, username, personal, family, email, password=None):
        """
        Create and save a normal (not-super) user.
        """
        user = self.model(
            username=username, personal=personal, family=family,
            email=self.normalize_email(email),
            is_superuser=False)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, personal, family, email, password):
        """
        Create and save a superuser.
        """
        user = self.model(
            username=username, personal=personal, family=family,
            email=self.normalize_email(email),
            is_superuser=True)
        user.set_password(password)
        user.save(using=self._db)
        return user


@reversion.register
class Person(AbstractBaseUser, PermissionsMixin):
    '''Represent a single person.'''
    MALE = 'M'
    FEMALE = 'F'
    OTHER = 'O'
    GENDER_CHOICES = (
        (MALE, 'Male'),
        (FEMALE, 'Female'),
        (OTHER, 'Other'),
        )

    # These attributes should always contain field names of Person
    PERSON_UPLOAD_FIELDS = ('personal', 'middle', 'family', 'email')
    PERSON_TASK_EXTRA_FIELDS = ('event', 'role')
    PERSON_TASK_UPLOAD_FIELDS = PERSON_UPLOAD_FIELDS + PERSON_TASK_EXTRA_FIELDS

    personal    = models.CharField(max_length=STR_LONG)
    middle      = models.CharField(max_length=STR_LONG, null=True, blank=True)
    family      = models.CharField(max_length=STR_LONG)
    email       = models.CharField(max_length=STR_LONG, unique=True, null=True, blank=True)
    gender      = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    may_contact = models.BooleanField(default=True)
    airport     = models.ForeignKey(Airport, null=True, blank=True, on_delete=models.PROTECT)
    github      = models.CharField(max_length=STR_MED, unique=True, null=True, blank=True)
    twitter     = models.CharField(max_length=STR_MED, unique=True, null=True, blank=True)
    url         = models.CharField(max_length=STR_LONG, null=True, blank=True)
    username    = models.CharField(max_length=STR_MED, unique=True)
    notes = models.TextField(default="", blank=True)
    affiliation = models.CharField(max_length=STR_LONG, default='', blank=True)

    badges = models.ManyToManyField("Badge", through="Award")
    lessons = models.ManyToManyField("Lesson", through="Qualification")
    domains = models.ManyToManyField("KnowledgeDomain")

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = [
        'personal',
        'family',
        'email',
        ]

    objects = PersonManager()

    def get_full_name(self):
        middle = ''
        if self.middle is not None:
            middle = ' {0}'.format(self.middle)
        return '{0}{1} {2}'.format(self.personal, middle, self.family)

    def get_short_name(self):
        return self.personal

    def __str__(self):
        result = self.get_full_name()
        if self.email is not None:
            result += ' <' + self.email + '>'
        return result

    def get_absolute_url(self):
        return reverse('person_details', args=[str(self.id)])

    @property
    def is_staff(self):
        """
        Required for logging into admin panel at '/admin/'.
        """
        return self.is_superuser

    def save(self, *args, **kwargs):
        # save empty string as NULL to the database - otherwise there are
        # issues with UNIQUE constraint failing
        self.middle = self.middle or None
        self.email = self.email or None
        self.gender = self.gender or None
        self.airport = self.airport or None
        self.github = self.github or None
        self.twitter = self.twitter or None
        self.url = self.url or None
        super().save(*args, **kwargs)


class ProfileUpdateRequest(models.Model):
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    personal = models.CharField(
        max_length=STR_LONG,
        verbose_name='Personal (first) name',
        blank=False,
    )
    family = models.CharField(
        max_length=STR_LONG,
        verbose_name='Family (last) name',
        blank=False,
    )
    email = models.CharField(
        max_length=STR_LONG,
        verbose_name='Email address',
        blank=False,
    )
    affiliation = models.CharField(
        max_length=STR_LONG,
        help_text='What university, company, lab, or other organization are '
        'you affiliated with (if any)?',
        blank=False,
    )
    airport_iata = models.CharField(
        max_length=3,
        verbose_name='Nearest major airport',
        help_text='Please use its 3-letter IATA code '
        '(<a href="http://www.airportcodes.aero/">'
        'http://www.airportcodes.aero/</a>) to tell us where you\'re located.',
        blank=False, null=False,
    )

    OCCUPATION_CHOICES = (
        (None, 'Prefer not to say'),
        ('undergrad', 'Undergraduate student'),
        ('grad', 'Graduate student'),
        ('postdoc', 'Post-doctoral researcher'),
        ('faculty', 'Faculty'),
        ('research', 'Research staff (including research programmer)'),
        ('support', 'Support staff (including technical support)'),
        ('librarian', 'Librarian/archivist'),
        ('commerce', 'Commercial software developer '),
        ('', 'Other (enter below)'),
    )
    occupation = models.CharField(
        max_length=STR_MED,
        choices=OCCUPATION_CHOICES,
        verbose_name='What is your current occupation/career stage?',
        help_text='Please choose the one that best describes you.',
        null=True, blank=True,
    )
    occupation_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other occupation/career stage',
        blank=True, default='',
    )
    github = models.CharField(
        max_length=STR_LONG,
        verbose_name='GitHub username',
        help_text='Please provide your username, not a numeric user ID.',
        blank=True, default='',
    )
    twitter = models.CharField(
        max_length=STR_LONG,
        verbose_name='Twitter username',
        help_text='Please, do not put "@" at the beginning.',
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
        (None, 'Prefer not to say'),
        ('F', 'Female'),
        ('M', 'Male'),
        ('O', 'Other (enter below)'),
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        null=True, blank=True,
    )
    gender_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other gender',
        blank=True, default='',
    )
    domains = models.ManyToManyField(
        'KnowledgeDomain',
        verbose_name='Areas of expertise',
        help_text='Please check all that apply.',
        blank=True,
    )
    domains_other = models.CharField(
        max_length=255,
        verbose_name='Other areas of expertise',
        blank=True, default='',
    )
    lessons = models.ManyToManyField(
        'Lesson',
        verbose_name='Topic and lessons you\'re comfortable teaching',
        help_text='Please mark ALL that apply.',
        blank=True,
    )
    lessons_other = models.CharField(
        max_length=255,
        verbose_name='Other topics/lessons you\'re comfortable teaching',
        help_text='Please include lesson URLs.',
        blank=True, default='',
    )

    def save(self, *args, **kwargs):
        """Save nullable char fields as empty strings."""
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


#------------------------------------------------------------

class Tag(models.Model):
    '''Label for grouping events.'''

    name       = models.CharField(max_length=STR_MED, unique=True)
    details    = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.name

#------------------------------------------------------------

# In order to make our custom filters chainable, we have to
# define them on the QuerySet, not the Manager - see
# http://www.dabapps.com/blog/higher-level-query-api-django-orm/
class EventQuerySet(models.query.QuerySet):
    '''Handles finding past, ongoing and upcoming events'''

    def past_events(self):
        '''Return past events.

        Past events are those which started before today, and
        which either ended before today or whose end is NULL
        '''

        # All events that started before today
        queryset = self.filter(start__lt=datetime.date.today())

        # Of those events, only those that also ended before today
        # or where the end date is NULL
        ended_before_today = models.Q(end__lt=datetime.date.today())
        end_is_null = models.Q(end__isnull=True)

        queryset = queryset.filter(ended_before_today | end_is_null)

        return queryset

    def upcoming_events(self):
        '''Return published upcoming events.

        Upcoming events are those which start after today.  Published
        events are those which have a URL. Events are ordered by date,
        soonest first.
        '''

        queryset = self.filter(start__gt=datetime.date.today())\
                       .filter(url__isnull=False)\
                       .order_by('start')
        return queryset

    def ongoing_events(self):
        '''Return ongoing events.

        Ongoing events are those which start after today.
        '''

        # All events that start before or on today
        queryset = self.filter(start__lte=datetime.date.today())

        # Of those, only the ones that finish after or on today
        queryset = queryset.filter(end__gte=datetime.date.today())

        return queryset

    def unpublished_events(self):
        '''Return events without URLs that are upcoming or have unknown starts.

        Events are ordered by slug and then by serial number.'''

        future_without_url = Q(start__gte=datetime.date.today(), url__isnull=True)
        unknown_start = Q(start__isnull=True)
        return self.filter(future_without_url | unknown_start)\
                   .order_by('slug', 'id')

    def published_events(self):
        '''Return events that have a start date and a URL.

        Events are ordered most recent first and then by serial number.'''

        queryset = self.exclude(
            Q(start__isnull=True) | Q(url__isnull=True)
            ).order_by('-start', 'id')

        return queryset

    def uninvoiced_events(self):
        '''Return a queryset for events that have not yet been invoiced.

        These are events that have an admin fee, are not marked as invoiced, and have occurred.
        Events are sorted oldest first.'''

        return self.past_events().filter(admin_fee__gt=0)\
                   .exclude(invoiced=True)\
                   .order_by('start')

class EventManager(models.Manager):
    '''A custom manager which is essentially a proxy for EventQuerySet'''

    def get_queryset(self):
        """Attach our custom query set to the manager."""
        return EventQuerySet(self.model, using=self._db)

    # Proxy methods so we can call our custom filters from the manager
    # without explicitly creating an EventQuerySet first - see
    # reference above

    def past_events(self):
        return self.get_queryset().past_events()

    def ongoing_events(self):
        return self.get_queryset().ongoing_events()

    def upcoming_events(self):
        return self.get_queryset().upcoming_events()

    def unpublished_events(self):
        return self.get_queryset().unpublished_events()

    def published_events(self):
        return self.get_queryset().published_events()

    def uninvoiced_events(self):
        return self.get_queryset().uninvoiced_events()


@reversion.register
class Event(models.Model):
    '''Represent a single event.'''

    host = models.ForeignKey(Host, on_delete=models.PROTECT,
                             help_text='Organization hosting the event.')
    tags       = models.ManyToManyField(Tag)
    administrator = models.ForeignKey(
        Host, related_name='administrator', null=True, blank=True,
        on_delete=models.PROTECT,
        help_text='Organization responsible for administrative work. Leave '
        'blank if self-organized.'
    )
    start      = models.DateField(null=True, blank=True,
                                  help_text='Setting this and url "publishes" the event.')
    end        = models.DateField(null=True, blank=True)
    slug       = models.CharField(max_length=STR_LONG, null=True, blank=True, unique=True)
    url        = models.CharField(max_length=STR_LONG, unique=True, null=True, blank=True,
                                  help_text='Setting this and startdate "publishes" the event.')
    reg_key    = models.CharField(max_length=STR_REG_KEY, null=True, blank=True, verbose_name="Eventbrite key")
    attendance = models.PositiveIntegerField(null=True, blank=True)
    admin_fee  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    invoiced   = models.NullBooleanField(default=False, blank=True)
    notes      = models.TextField(default="", blank=True)
    contact = models.CharField(max_length=255, default="", blank=True)
    country = CountryField(null=True, blank=True)
    venue = models.CharField(max_length=255, default='', blank=True)
    address = models.CharField(max_length=255, default='', blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    REPO_REGEX = re.compile(r'https?://github\.com/(?P<name>[^/]+)/'
                            r'(?P<repo>[^/]+)/?')
    REPO_FORMAT = 'https://github.com/{name}/{repo}'
    WEBSITE_REGEX = re.compile(r'https?://(?P<name>[^.]+)\.github\.'
                               r'(io|com)/(?P<repo>[^/]+)/?')
    WEBSITE_FORMAT = 'https://{name}.github.io/{repo}'

    class Meta:
        ordering = ('-start', )

    # Set the custom manager
    objects = EventManager()

    def __str__(self):
        return self.get_ident()

    def get_absolute_url(self):
        return reverse('event_details', args=[self.get_ident()])

    def get_repository_url(self):
        """Return self.url formatted as it was repository URL.

        Repository URL is as specified in REPO_FORMAT.
        If it doesn't match, the original URL is returned."""
        try:
            mo = self.WEBSITE_REGEX.match(self.url)
            if not mo:
                return self.url

            return self.REPO_FORMAT.format(**mo.groupdict())
        except (TypeError, KeyError):
            # TypeError: self.url is None
            # KeyError: mo.groupdict doesn't supply required names to format
            return self.url

    def get_website_url(self):
        """Return self.url formatted as it was website URL.

        Website URL is as specified in WEBSITE_FORMAT.
        If it doesn't match, the original URL is returned."""
        try:
            mo = self.REPO_REGEX.match(self.url)
            if not mo:
                return self.url

            return self.WEBSITE_FORMAT.format(**mo.groupdict())
        except (TypeError, KeyError):
            # TypeError: self.url is None
            # KeyError: mo.groupdict doesn't supply required names to format
            return self.url

    def get_ident(self):
        if self.slug:
            return str(self.slug)
        return str(self.id)

    @staticmethod
    def get_by_ident(ident):
        '''
        Select event that matches given identifier.
        If ident is an int, search for matching primary-key;
        otherwise get matching slug. May throw DoesNotExist error.
        '''
        try:
            return Event.objects.get(pk=int(ident))
        except ValueError:
            return Event.objects.get(slug=ident)

    def save(self, *args, **kwargs):
        self.slug = self.slug or None
        self.url = self.url or None
        super(Event, self).save(*args, **kwargs)


class EventRequest(models.Model):
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
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
        max_length=255,
        help_text='Please indicate when you would like to run the workshop. '
                  'A range of at least a month is most helpful, although if '
                  'you have specific dates you need the workshop, we will try '
                  'to accommodate those requests.',
        verbose_name='Preferred workshop dates',
    )
    language = models.CharField(
        max_length=STR_LONG,
        verbose_name='What human language do you want the workshop to be run'
                     ' in?',
        blank=True, default='English',
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
        ('1-20', '1-20 (one room, one instructor)'),
        ('20-40', '20-40 (one room, two instructors)'),
        ('40-80', '40-80 (two rooms, four instructors)'),
        ('80-120', '80-120 (three rooms, six instructors)'),
    )
    approx_attendees = models.CharField(
        max_length=STR_MED,
        choices=ATTENDEES_NUMBER_CHOICES,
        help_text='This number doesn\'t need to be precise, but will help us '
                  'decide how many instructors your workshop will need.',
        verbose_name='Approximate number of Attendees',
        blank=False,
        default='20-40',
    )

    attendee_domains = models.ManyToManyField(
        'KnowledgeDomain',
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
        ('', 'Other (type below)'),
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
        'AcademicLevel',
        help_text='If you know the academic level(s) of your attendees, '
                  'indicate them here.',
        verbose_name='Attendees\' Academic Level',
    )
    attendee_computing_levels = models.ManyToManyField(
        'ComputingExperienceLevel',
        help_text='Indicate the attendees\' level of computing experience, if '
                  'known. We will ask attendees to fill in a skills survey '
                  'before the workshop, so this answer can be an '
                  'approximation.',
        verbose_name='Attendees\' level of computing experience',
    )
    attendee_data_analysis_level = models.ManyToManyField(
        'DataAnalysisLevel',
        help_text='If you know, indicate learner\'s general level of data '
                  'analysis experience',
        verbose_name='Level of data analysis experience',
    )
    understand_admin_fee = models.BooleanField(
        default=False,
        # verbose_name a.k.a. label and help_text were moved to the
        # SWCEventRequestForm and DCEventRequestForm
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
        ('', 'Other (type below)'),
    )
    travel_reimbursement = models.CharField(
        max_length=STR_MED,
        verbose_name='How will instructors\' travel and accommodations be '
                     'managed?',
        choices=TRAVEL_REIMBURSEMENT_CHOICES,
        null=True, blank=True, default=None,
    )
    travel_reimbursement_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other propositions for managing instructors\' travel and'
                     ' accommodations',
        blank=True,
    )

    ADMIN_FEE_PAYMENT_CHOICES = (
        ('NP1', 'Non-profit / non-partner: US$2500'),
        ('partner', 'Partner: US$1250'),
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


class AcademicLevel(models.Model):
    name = models.CharField(max_length=STR_MED, null=False, blank=False)

    def __str__(self):
        return self.name


class ComputingExperienceLevel(models.Model):
    # it's a long field because we need to store reasoning too, for example:
    # "Novice (uses a spreadsheet for data analysis rather than writing code)"
    name = models.CharField(max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name


class DataAnalysisLevel(models.Model):
    # ComputingExperienceLevel's sibling
    name = models.CharField(max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name


#------------------------------------------------------------

class Role(models.Model):
    '''Enumerate roles in workshops.'''

    name       = models.CharField(max_length=STR_MED)

    def __str__(self):
        return self.name

#------------------------------------------------------------


class TaskManager(models.Manager):
    def instructors(self):
        """Fetch tasks with role 'instructor'."""
        return self.get_queryset().filter(role__name="instructor")

    def learners(self):
        """Fetch tasks with role 'learner'."""
        return self.get_queryset().filter(role__name="learner")

    def helpers(self):
        """Fetch tasks with role 'helper'."""
        return self.get_queryset().filter(role__name="helper")


class Task(models.Model):
    '''Represent who did what at events.'''

    event      = models.ForeignKey(Event)
    person     = models.ForeignKey(Person)
    role       = models.ForeignKey(Role)

    objects = TaskManager()

    class Meta:
        unique_together = ("event", "person", "role")

    def __str__(self):
        return '{0}/{1}={2}'.format(self.event, self.person, self.role)

    def get_absolute_url(self):
        return reverse('task_details', kwargs={'task_id': self.id})

#------------------------------------------------------------

class Lesson(models.Model):
    '''Represent a lesson someone might teach.'''

    name       = models.CharField(max_length=STR_MED)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

#------------------------------------------------------------

class Qualification(models.Model):
    '''What is someone qualified to teach?'''

    person     = models.ForeignKey(Person)
    lesson     = models.ForeignKey(Lesson)

    def __str__(self):
        return '{0}/{1}'.format(self.person, self.lesson)

#------------------------------------------------------------

class Badge(models.Model):
    '''Represent a badge we award.'''

    name       = models.CharField(max_length=STR_MED, unique=True)
    title      = models.CharField(max_length=STR_MED)
    criteria   = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('badge_details', args=[self.name])

#------------------------------------------------------------

class Award(models.Model):
    '''Represent a particular badge earned by a person.'''

    person     = models.ForeignKey(Person)
    badge      = models.ForeignKey(Badge)
    awarded    = models.DateField()
    event      = models.ForeignKey(Event, null=True, blank=True,
                                   on_delete=models.PROTECT)

    class Meta:
        unique_together = ("person", "badge", )

    def __str__(self):
        return '{0}/{1}/{2}/{3}'.format(self.person, self.badge, self.awarded, self.event)

#------------------------------------------------------------

class KnowledgeDomain(models.Model):
    """Represent a knowledge domain a person is engaged in."""
    name = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.name
