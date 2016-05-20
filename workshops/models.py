import datetime
import re
from urllib.parse import urlencode

from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from django_countries.fields import CountryField
from reversion import revisions as reversion

#------------------------------------------------------------

STR_SHORT   =  10         # length of short strings
STR_MED     =  40         # length of medium strings
STR_LONG    = 100         # length of long strings
STR_REG_KEY =  20         # length of Eventbrite registration key

#------------------------------------------------------------


class AssignmentMixin(models.Model):
    """This abstract model acts as a mix-in, so it adds
    "assigned to admin [...]" field to any inheriting model."""
    assigned_to = models.ForeignKey("Person", null=True, blank=True,)

    class Meta:
        abstract = True


@reversion.register
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


@reversion.register
class Membership(models.Model):
    """Represent a details of Host's membership."""

    MEMBERSHIP_CHOICES = (
        ('partner', 'Partner'),
        ('affiliate', 'Affiliate'),
        ('sponsor', 'Sponsor'),
    )
    variant = models.CharField(
        max_length=STR_MED, null=False, blank=False,
        choices=MEMBERSHIP_CHOICES,
    )
    agreement_start = models.DateField(
        default=timezone.now, null=True, blank=True, editable=True,
    )
    agreement_end = models.DateField(
        default=timezone.now, null=True, blank=True, editable=True,
    )
    CONTRIBUTION_CHOICES = (
        ('financial', 'Financial'),
        ('person-days', 'Person-days'),
        ('other', 'Other'),
    )
    contribution_type = models.CharField(
        max_length=STR_MED, null=True, blank=True,
        choices=CONTRIBUTION_CHOICES,
    )
    workshops_without_admin_fee_per_year = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Acceptable number of workshops without admin fee per year",
    )
    self_organized_workshops_per_year = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Imposed number of self-organized workshops per year",
    )
    notes = models.TextField(default="", blank=True)
    host = models.ForeignKey(Host, null=False, blank=False,
                             on_delete=models.PROTECT)

    def __str__(self):
        return "{} Membership of <{}>".format(self.variant, str(self.host))

    @property
    def workshops_without_admin_fee_per_year_completed(self):
        """Count workshops without admin fee hosted the year agreement
        started."""
        year = self.agreement_start.year
        self_organized = (Q(administrator=None) |
                          Q(administrator__domain='self-organized'))
        no_fee = Q(admin_fee=0) | Q(admin_fee=None)

        return Event.objects.filter(host=self.host, start__year=year) \
                            .filter(no_fee) \
                            .exclude(self_organized).count()

    @property
    def workshops_without_admin_fee_per_year_remaining(self):
        """Count remaining workshops w/o admin fee for the year agreement
        started."""
        a = self.workshops_without_admin_fee_per_year
        b = self.workshops_without_admin_fee_per_year_completed
        return a - b

    @property
    def self_organized_workshops_per_year_completed(self):
        """Count self-organized workshops hosted the year agreement started."""
        year = self.agreement_start.year
        self_organized = (Q(administrator=None) |
                          Q(administrator__domain='self-organized'))

        return Event.objects.filter(host=self.host, start__year=year) \
                            .filter(self_organized).count()

    @property
    def self_organized_workshops_per_year_remaining(self):
        """Count remaining self-organized workshops for the year agreement
        started."""
        a = self.self_organized_workshops_per_year
        b = self.self_organized_workshops_per_year_completed
        return a - b


#------------------------------------------------------------


@reversion.register
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
            is_superuser=False,
            is_active=True,
        )
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
            is_superuser=True,
            is_active=True,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username):
        """Let's make this command so that it gets user by *either* username or
        email.  Original behavior is to get user by USERNAME_FIELD."""
        if '@' in username:
            return self.get(email=username)
        else:
            return super().get_by_natural_key(username)


@reversion.register
class Person(AbstractBaseUser, PermissionsMixin):
    '''Represent a single person.'''
    UNDISCLOSED = 'U'
    MALE = 'M'
    FEMALE = 'F'
    OTHER = 'O'
    GENDER_CHOICES = (
        (UNDISCLOSED, 'Prefer not to say (undisclosed)'),
        (MALE, 'Male'),
        (FEMALE, 'Female'),
        (OTHER, 'Other'),
    )

    # These attributes should always contain field names of Person
    PERSON_UPLOAD_FIELDS = ('personal', 'family', 'email')
    PERSON_TASK_EXTRA_FIELDS = ('event', 'role')
    PERSON_TASK_UPLOAD_FIELDS = PERSON_UPLOAD_FIELDS + PERSON_TASK_EXTRA_FIELDS

    personal    = models.CharField(max_length=STR_LONG)
    middle      = models.CharField(max_length=STR_LONG, null=True, blank=True)
    family      = models.CharField(max_length=STR_LONG)
    email       = models.CharField(max_length=STR_LONG, unique=True, null=True, blank=True)
    gender      = models.CharField(max_length=1, choices=GENDER_CHOICES, null=False, default=UNDISCLOSED)
    may_contact = models.BooleanField(default=True)
    airport     = models.ForeignKey(Airport, null=True, blank=True, on_delete=models.PROTECT)
    github      = models.CharField(max_length=STR_MED, unique=True, null=True, blank=True)
    twitter     = models.CharField(max_length=STR_MED, unique=True, null=True, blank=True)
    url         = models.CharField(max_length=STR_LONG, null=True, blank=True)
    username = models.CharField(
        max_length=STR_MED, unique=True,
        validators=[RegexValidator(r'^[\w\-_]+$', flags=re.A)],
    )
    notes = models.TextField(default="", blank=True)
    affiliation = models.CharField(max_length=STR_LONG, default='', blank=True)

    badges = models.ManyToManyField(
        "Badge", through="Award",
        through_fields=('person', 'badge'))
    lessons = models.ManyToManyField(
        "Lesson",
        through="Qualification",
        blank=True,
    )
    domains = models.ManyToManyField(
        "KnowledgeDomain",
        limit_choices_to=~Q(name__startswith='Don\'t know yet'),
        blank=True,
    )
    languages = models.ManyToManyField(
        "Language",
        blank=True,
    )

    # new people will be inactive by default
    is_active = models.BooleanField(default=False)

    # Recorded in ProfileUpdateRequest. Occupation will store the either
    # 'undisclosed' or full text of occupation selected by user.  In case of
    # selecting 'other' the value from `occupation_other` field will be used.
    occupation = models.CharField(
        max_length=STR_LONG,
        verbose_name='Current occupation/career stage',
        blank=True, default='',
    )
    orcid = models.CharField(
        max_length=STR_LONG,
        verbose_name='ORCID ID',
        blank=True, default='',
    )

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

    def clean(self):
        """This will be called by the ModelForm.is_valid(). No saving to the
        database."""
        # lowercase the email
        self.email = self.email.lower()

    def save(self, *args, **kwargs):
        # save empty string as NULL to the database - otherwise there are
        # issues with UNIQUE constraint failing
        self.personal = self.personal.strip()
        self.family = self.family.strip()
        self.middle = self.middle.strip() if self.middle else None
        self.email = self.email.strip() if self.email else None
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
    airport_iata = models.CharField(
        max_length=3,
        verbose_name='Nearest major airport',
        help_text='Please use its 3-letter IATA code '
        '(<a href="http://www.airportcodes.aero/" target="_blank">'
        'http://www.airportcodes.aero/</a>) to tell us where you\'re located.',
        blank=False, null=False,
    )

    OCCUPATION_CHOICES = (
        ('undisclosed', 'Prefer not to say'),
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
        null=False, blank=True, default='undisclosed',
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
        (Person.OTHER, 'Other (enter below)'),
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
        'KnowledgeDomain',
        verbose_name='Areas of expertise',
        help_text='Please check all that apply.',
        limit_choices_to=~Q(name__startswith='Don\'t know yet'),
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
        blank=False,
    )
    lessons_other = models.CharField(
        max_length=255,
        verbose_name='Other topics/lessons you\'re comfortable teaching',
        help_text='Please include lesson URLs.',
        blank=True, default='',
    )
    notes = models.TextField(
        default="",
        blank=True)

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


#------------------------------------------------------------

class Tag(models.Model):
    '''Label for grouping events.'''

    name       = models.CharField(max_length=STR_MED, unique=True)
    details    = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.name

#------------------------------------------------------------

class Language(models.Model):
    """A language tag.

    https://tools.ietf.org/html/rfc5646
    """
    name = models.CharField(
        max_length=STR_MED,
        help_text='Description of this language tag in English')
    subtag = models.CharField(
        max_length=STR_SHORT,
        help_text=
            'Primary language subtag.  '
            'https://tools.ietf.org/html/rfc5646#section-2.2.1')

    def __str__(self):
        return self.name

#------------------------------------------------------------

# In order to make our custom filters chainable, we have to
# define them on the QuerySet, not the Manager - see
# http://www.dabapps.com/blog/higher-level-query-api-django-orm/
class EventQuerySet(models.query.QuerySet):
    '''Handles finding past, ongoing and upcoming events'''

    def active(self):
        """Exclude inactive events (stalled or completed)."""
        return self.exclude(tags__name='stalled').exclude(completed=True)

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
        """Return published upcoming events.

        Upcoming events are published events (see `published_events` below)
        that start after today."""

        queryset = self.published_events() \
                       .filter(start__gt=datetime.date.today()) \
                       .order_by('start')
        return queryset

    def ongoing_events(self):
        """Return ongoing events.

        Ongoing events are published events (see `published_events` below)
        that are currently taking place (ie. start today or before and end
        today or later)."""

        # All events that start before or on today, and finish after or on
        # today.
        queryset = self.published_events() \
                       .filter(start__lte=datetime.date.today()) \
                       .filter(end__gte=datetime.date.today()) \
                       .order_by('start')

        return queryset

    def unpublished_conditional(self):
        """Return conditional for events without: start OR country OR venue OR
        url (ie. unpublished events). This will be used in
        `self.published_events`, too."""
        unknown_start = Q(start__isnull=True)
        no_country = Q(country__isnull=True)
        no_venue = Q(venue__exact='')
        no_address = Q(address__exact='')
        no_latitude = Q(latitude__isnull=True)
        no_longitude = Q(longitude__isnull=True)
        no_url = Q(url__isnull=True)
        return (
            unknown_start | no_country | no_venue | no_address | no_latitude |
            no_longitude | no_url
        )

    def unpublished_events(self):
        """Return events considered as unpublished (see
        `unpublished_conditional` above)."""
        conditional = self.unpublished_conditional()
        return self.filter(conditional).order_by('slug', 'id')

    def published_events(self):
        """Return events considered as published (see `unpublished_conditional`
        above)."""
        conditional = self.unpublished_conditional()
        return self.exclude(conditional).order_by('-start', 'id')

    def uninvoiced_events(self):
        '''Return a queryset for events that have not yet been invoiced.

        These are marked as uninvoiced, and have occurred.
        Events are sorted oldest first.'''

        return self.past_events().filter(invoice_status='not-invoiced') \
                                 .order_by('start')

    def metadata_changed(self):
        """Return events for which remote metatags have been updated."""
        return self.filter(metadata_changed=True)


@reversion.register
class Event(AssignmentMixin, models.Model):
    '''Represent a single event.'''

    REPO_REGEX = re.compile(r'https?://github\.com/(?P<name>[^/]+)/'
                            r'(?P<repo>[^/]+)/?')
    REPO_FORMAT = 'https://github.com/{name}/{repo}'
    WEBSITE_REGEX = re.compile(r'https?://(?P<name>[^.]+)\.github\.'
                               r'(io|com)/(?P<repo>[^/]+)/?')
    WEBSITE_FORMAT = 'https://{name}.github.io/{repo}/'
    PUBLISHED_HELP_TEXT = 'Required in order for this event to be "published".'

    host = models.ForeignKey(Host, on_delete=models.PROTECT,
                             help_text='Organization hosting the event.')
    tags = models.ManyToManyField(
        Tag,
        help_text='<ul><li><i>stalled</i> — for events with lost contact with '
                  'the host or TTT events that aren\'t running.</li>'
                  '<li><i>unresponsive</i> – for events whose hosts and/or '
                  'organizers aren\'t going to send us attendance data.</li>'
                  '</ul>',
    )
    administrator = models.ForeignKey(
        Host, related_name='administrator', null=True, blank=True,
        on_delete=models.PROTECT,
        help_text='Organization responsible for administrative work.'
    )
    start = models.DateField(
        null=True, blank=True,
        help_text=PUBLISHED_HELP_TEXT,
    )
    end        = models.DateField(null=True, blank=True)
    slug       = models.CharField(max_length=STR_LONG, null=True, blank=True, unique=True)
    url = models.CharField(
        max_length=STR_LONG, unique=True, null=True, blank=True,
        validators=[RegexValidator(REPO_REGEX, inverse_match=True)],
        help_text=PUBLISHED_HELP_TEXT +
                  '<br />Use link to the event\'s <b>website</b>, ' +
                  'not repository.',
    )
    reg_key    = models.CharField(max_length=STR_REG_KEY, null=True, blank=True, verbose_name="Eventbrite key")
    attendance = models.PositiveIntegerField(null=True, blank=True)
    admin_fee  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    INVOICED_CHOICES = (
        ('unknown', 'Unknown'),
        ('invoiced', 'Invoiced'),
        ('not-invoiced', 'Not invoiced'),
        ('na-historic', 'Not applicable for historical reasons'),
        ('na-member', 'Not applicable because of membership'),
        ('na-self-org', 'Not applicable because self-organized'),
        ('na-waiver', 'Not applicable because waiver granted'),
        ('na-other', 'Not applicable because other arrangements made'),
    )
    invoice_status = models.CharField(
        max_length=STR_MED,
        choices=INVOICED_CHOICES,
        verbose_name='Invoice status',
        default='unknown', blank=False,
    )
    notes      = models.TextField(default="", blank=True)
    contact = models.CharField(max_length=255, default="", blank=True)
    country = CountryField(
        null=True, blank=True,
        help_text=PUBLISHED_HELP_TEXT +
                  '<br />Use <b>Online</b> for online events.',
    )
    venue = models.CharField(
        max_length=255, default='', blank=True, help_text=PUBLISHED_HELP_TEXT,
    )
    address = models.CharField(
        max_length=255, default='', blank=True, help_text=PUBLISHED_HELP_TEXT,
    )
    latitude = models.FloatField(
        null=True, blank=True, help_text=PUBLISHED_HELP_TEXT,
    )
    longitude = models.FloatField(
        null=True, blank=True, help_text=PUBLISHED_HELP_TEXT,
    )

    completed = models.BooleanField(
        default=False,
        help_text="Indicates that no more work is needed upon this event.",
    )

    # links to the surveys
    learners_pre = models.URLField(
        blank=True, default="",
        verbose_name="Pre-workshop assessment survey for learners")
    learners_post = models.URLField(
        blank=True, default="",
        verbose_name="Post-workshop assessment survey for learners")
    instructors_pre = models.URLField(
        blank=True, default="",
        verbose_name="Pre-workshop assessment survey for instructors")
    instructors_post = models.URLField(
        blank=True, default="",
        verbose_name="Post-workshop assessment survey for instructors")
    learners_longterm = models.URLField(
        blank=True, default="",
        verbose_name="Long-term assessment survey for learners")

    request = models.ForeignKey(
        'EventRequest', null=True, blank=True,
        help_text='Backlink to the request that created this event.',
    )

    # used in getting metadata updates from GitHub
    repository_last_commit_hash = models.CharField(
        max_length=40, blank=True, default='',
        help_text='Event\'s repository last commit SHA1 hash')
    repository_metadata = models.TextField(
        blank=True, default='',
        help_text='JSON-serialized metadata from event\'s website')
    metadata_all_changes = models.TextField(
        blank=True, default='', help_text='List of detected metadata changes')
    metadata_changed = models.BooleanField(
        default=False,
        help_text='Indicate if metadata changed since last check')

    class Meta:
        ordering = ('-start', )

    # make a custom manager from our QuerySet derivative
    objects = EventQuerySet.as_manager()

    def __str__(self):
        return self.get_ident()

    def get_absolute_url(self):
        return reverse('event_details', args=[self.get_ident()])

    @property
    def repository_url(self):
        """Return self.url formatted as it was repository URL.

        Repository URL is as specified in REPO_FORMAT.
        If it doesn't match, the original URL is returned."""
        try:
            # Try to match repo regex first. This will result in all repo URLs
            # always formatted in the same way.
            mo = (self.REPO_REGEX.match(self.url)
                  or self.WEBSITE_REGEX.match(self.url))
            if not mo:
                return self.url

            return self.REPO_FORMAT.format(**mo.groupdict())
        except (TypeError, KeyError):
            # TypeError: self.url is None
            # KeyError: mo.groupdict doesn't supply required names to format
            return self.url

    @property
    def website_url(self):
        """Return self.url formatted as it was website URL.

        Website URL is as specified in WEBSITE_FORMAT.
        If it doesn't match, the original URL is returned."""
        try:
            # Try to match website regex first. This will result in all website
            # URLs always formatted in the same way.
            mo = (self.WEBSITE_REGEX.match(self.url)
                  or self.REPO_REGEX.match(self.url))
            if not mo:
                return self.url

            return self.WEBSITE_FORMAT.format(**mo.groupdict())
        except (TypeError, KeyError):
            # TypeError: self.url is None
            # KeyError: mo.groupdict doesn't supply required names to format
            return self.url

    @property
    def uninvoiced(self):
        """Indicate if the event has been invoiced or not."""
        return self.invoice_status == 'not-invoiced'

    @property
    def mailto(self):
        """Return list of emails we can contact about workshop details, like
        attendance."""
        from workshops.util import find_emails

        emails = Task.objects \
            .filter(event=self) \
            .filter(
                # we only want hosts, organizers and instructors
                Q(role__name='host') | Q(role__name='organizer') |
                Q(role__name='instructor')
            ) \
            .filter(person__may_contact=True) \
            .exclude(Q(person__email='') | Q(person__email=None)) \
            .values_list('person__email', flat=True)

        additional_emails = find_emails(self.contact)
        # Emails will become an iterator in 1.9 (ValuesListQuerySet previously)
        # so we need a normal list that will be extended by that iterator.
        # Bonus points: it works in 1.8.x too!
        additional_emails.extend(emails)
        return ','.join(additional_emails)

    def get_invoice_form_url(self):
        from .util import universal_date_format

        query = {
            'entry.823772951': self.venue,  # Organization to invoice
            'entry.351294200': 'Workshop administrative fee',  # Reason

            # Date of event
            'entry.1749215879': (universal_date_format(self.start)
                                 if self.start else ''),
            'entry.508035854': self.slug,  # Event or item ID
            'entry.821460022': self.admin_fee,  # Total invoice amount
            'entry.1316946828': 'US dollars',  # Currency
        }
        url = ("https://docs.google.com/forms/d/"
               "1XljyEam4LERRXW0ebyh5eoZXjT1xR4bHkPxITLWiIyA/viewform?")
        url += urlencode(query)
        return url

    @property
    def human_readable_date(self):
        """Render start and end dates as human-readable short date."""
        date1 = self.start
        date2 = self.end

        if date1 and not date2:
            return '{:%b %d, %Y}-???'.format(date1)
        elif date2 and not date1:
            return '???-{:%b %d, %Y}'.format(date2)
        elif not date2 and not date1:
            return '???-???'

        if date1.year == date2.year:
            if date1.month == date2.month:
                return '{:%b %d}-{:%d, %Y}'.format(date1, date2)
            else:
                return '{:%b %d}-{:%b %d, %Y}'.format(date1, date2)
        else:
            return '{:%b %d, %Y}-{:%b %d, %Y}'.format(date1, date2)

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

        if self.country == 'W3':
            # enforce location data for 'Online' country
            self.venue = 'Internet'
            self.address = 'Internet'
            self.latitude = -48.876667
            self.longitude = -123.393333

        super(Event, self).save(*args, **kwargs)


class EventRequest(AssignmentMixin, models.Model):
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
    language = models.ForeignKey(
        'Language',
        verbose_name='What human language do you want the workshop to be run'
                     ' in?',
        null=True,
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


class EventSubmission(AssignmentMixin, models.Model):
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
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

    name = models.CharField(max_length=STR_MED)
    verbose_name = models.CharField(max_length=STR_LONG,
                                    null=False, blank=True, default='')

    def __str__(self):
        return self.verbose_name

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


@reversion.register
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


class BadgeQuerySet(models.query.QuerySet):
    """Custom QuerySet that provides easy way to get instructor badges
    (we use that a lot)."""

    INSTRUCTOR_BADGES = ('dc-instructor', 'swc-instructor')

    def instructor_badges(self):
        """Filter for instructor badges only."""

        return self.filter(name__in=self.INSTRUCTOR_BADGES)


class Badge(models.Model):
    '''Represent a badge we award.'''

    name       = models.CharField(max_length=STR_MED, unique=True)
    title      = models.CharField(max_length=STR_MED)
    criteria   = models.CharField(max_length=STR_LONG)

    objects = BadgeQuerySet.as_manager()

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
    awarded_by = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT,
        related_name='awarded_set')

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

# ------------------------------------------------------------


class TodoItemQuerySet(models.query.QuerySet):
    @staticmethod
    def current_week_dates(today=None):
        if not today:
            today = datetime.date.today()
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=7)
        return start, end

    @staticmethod
    def next_week_dates(today=None):
        if not today:
            today = datetime.date.today()
        start = today + datetime.timedelta(days=(7 - today.weekday()))
        end = start + datetime.timedelta(days=7)
        return start, end

    def user(self, person):
        """Return TODOs only for specific person."""
        return self.filter(event__assigned_to=person)

    def current_week(self, today=None):
        """Select TODOs for the current week."""
        start, end = TodoItemQuerySet.current_week_dates(today)
        return self.filter(due__gte=start, due__lt=end)

    def next_week(self, today=None):
        """Select TODOs for the next week."""
        start, end = TodoItemQuerySet.next_week_dates(today)
        return self.filter(due__gte=start, due__lt=end)

    def incomplete(self):
        """Select TODOs that aren't marked as completed."""
        return self.filter(completed=False)

    def current(self, today=None):
        """A shortcut for getting TODOs from this and upcoming week."""
        return ((self.current_week(today) | self.next_week(today)) &
                self.incomplete())


class TodoItem(models.Model):
    """Model representing to-do items for events."""
    event = models.ForeignKey(Event, null=False, blank=False)
    completed = models.BooleanField(default=False)
    title = models.CharField(max_length=STR_LONG, default='', blank=False)
    due = models.DateField(blank=True, null=True)
    additional = models.CharField(max_length=255, default='', blank=True)

    objects = TodoItemQuerySet.as_manager()

    class Meta:
        ordering = ["due", "title"]

    def __str__(self):
        from .util import universal_date_format

        if self.due:
            return "{title} due {due}".format(
                title=self.title, due=universal_date_format(self.due),
            )
        else:
            return self.title

# ------------------------------------------------------------


@reversion.register
class InvoiceRequest(models.Model):
    STATUS_CHOICES = (
        ('not-invoiced', 'Not invoiced'),
        ('sent', 'Sent out'),
        ('paid', 'Paid'),
    )
    status = models.CharField(
        max_length=STR_MED, null=False, blank=False, default='not-invoiced',
        choices=STATUS_CHOICES,
        verbose_name='Invoice status')

    sent_date = models.DateField(
        null=True, blank=True, verbose_name='Date invoice was sent out',
        help_text='YYYY-MM-DD')
    paid_date = models.DateField(
        null=True, blank=True, verbose_name='Date invoice was paid',
        help_text='YYYY-MM-DD')

    organization = models.ForeignKey(
        Host, on_delete=models.PROTECT, verbose_name='Organization to invoice',
        help_text='e.g. University of Florida Ecology Department')

    INVOICE_REASON = (
        ('admin-fee', 'Workshop administrative fee'),
        ('admin-fee-expenses', 'Workshop administrative fee plus expenses'),
        ('partner', 'Partner agreement'),
        ('affiliate', 'Affiliate agreement'),
        ('consulting', 'Consulting'),
        ('', 'Other (enter below)'),
    )
    reason = models.CharField(
        max_length=STR_MED, null=False, blank=True, default='admin-fee',
        choices=INVOICE_REASON,
        verbose_name='Reason for invoice')
    reason_other = models.CharField(
        max_length=STR_LONG, null=False, blank=True, default='',
        verbose_name='Other reason for invoice')
    date = models.DateField(
        null=False, blank=False, verbose_name='Date of invoice subject',
        help_text='YYYY-MM-DD; either event\'s date or invoice reason date.')
    event = models.ForeignKey(
        Event, on_delete=models.PROTECT, null=True, blank=True)
    event_location = models.CharField(
        max_length=STR_LONG, null=False, blank=True, default='')
    item_id = models.CharField(
        max_length=STR_MED, null=False, blank=True, default='',
        verbose_name='Item ID (if applicable)')
    postal_number = models.CharField(
        max_length=STR_MED, null=False, blank=True, default='',
        verbose_name='PO # (if required)')
    contact_name = models.CharField(
        max_length=STR_LONG, null=False, blank=False,
        verbose_name='Organization contact name',
        help_text='e.g. Dr. Jane Smith - the name of the person to contact at '
                  'the organization about the invoice')
    contact_email = models.EmailField(
        max_length=STR_LONG, null=False, blank=False,
        verbose_name='Organization contact email')
    contact_phone = models.CharField(
        max_length=STR_LONG, null=False, blank=True,
        verbose_name='Organization contact phone #')
    full_address = models.TextField(
        null=False, blank=False,
        verbose_name='Full address to invoice',
        help_text='e.g. Dr. Jane Smith; University of Florida Ecology '
                  'Department; 123 University Way; Gainesville, FL 32844')
    amount = models.DecimalField(
        max_digits=8, decimal_places=2, null=False, blank=False,
        validators=[MinValueValidator(0)],
        verbose_name='Full invoice amount',
        help_text='e.g. 1992.33 ')

    CURRENCY = (
        ('USD', 'US Dollars'),
        ('GBP', 'UK Pounds'),
        ('EUR', 'Euros'),
        ('', 'Other (enter below)'),
    )
    currency = models.CharField(
        max_length=STR_MED, null=False, blank=True, default='USD',
        choices=CURRENCY)
    currency_other = models.CharField(
        max_length=STR_LONG, null=False, blank=True, default='',
        verbose_name='Other currency')

    breakdown = models.TextField(
        blank=True, default='',
        verbose_name='Notes on invoice breakdown',
        help_text='e.g. 1250.00 workshop fee;'
                  ' 742.33 Instructor, Pat Li, travel expenses')

    VENDOR_FORM_CHOICES = (
        ('yes', 'Yes'),
        ('no', 'No'),
        ('unsure', 'Will check with contact and submit info if needed'),
    )
    vendor_form_required = models.CharField(
        max_length=STR_SHORT, null=False, blank=False, default='no',
        choices=VENDOR_FORM_CHOICES,
        verbose_name='Do vendor/supplier forms need to be submitted?')
    vendor_form_link = models.URLField(
        null=False, blank=True, default='',
        verbose_name='Link to vendor/supplier forms')
    form_W9 = models.BooleanField(verbose_name='Organization needs a W-9 form')

    RECEIPTS_CHOICES = (
        ('email', 'Via email'),
        ('shared', 'In a Google Drive or other shared location'),
        ('not-yet', 'Haven\'t sent yet'),
        ('na', 'Not applicable'),
    )
    receipts_sent = models.CharField(
        max_length=STR_MED, null=False, blank=False, default='not-yet',
        choices=RECEIPTS_CHOICES,
        verbose_name='Any required receipts sent?')
    shared_receipts_link = models.URLField(
        null=False, blank=True, default='',
        verbose_name='Link to receipts in shared location',
        help_text='e.g. link to Google drive folder')
    notes = models.TextField(
        blank=True, default='',
        verbose_name='Any other notes')

    def __str__(self):
        return "Invoice to {!s} for {!s}".format(self.organization,
                                                 self.event)

    def get_absolute_url(self):
        return reverse('invoicerequest_details', args=[self.pk])

    @property
    def paid(self):
        return self.status == 'paid'

    @property
    def long_status(self):
        """Display status with date, if available."""
        LONG_FMT = '{} on {:%Y-%m-%d}'
        if self.status == 'sent' and self.sent_date:
            return LONG_FMT.format(self.get_status_display(), self.sent_date)
        elif self.status == 'paid' and self.paid_date:
            return LONG_FMT.format(self.get_status_display(), self.paid_date)

        return self.get_status_display()

#------------------------------------------------------------


def build_choice_field_with_other_option(choices, default, verbose_name=None):
    assert default in [c[0] for c in choices]
    assert all(c[0] != '' for c in choices)

    field = models.CharField(
        max_length=STR_MED,
        choices=choices,
        verbose_name=verbose_name,
        null=False, blank=False, default=default,
    )
    other_field = models.CharField(
        max_length=STR_LONG,
        verbose_name=' ',
        null=False, blank=True, default='',
    )
    return field, other_field


@reversion.register
class TrainingRequest(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    personal = models.CharField(
        max_length=STR_LONG,
        verbose_name='Personal name',
        blank=False,
    )
    family = models.CharField(
        max_length=STR_LONG,
        verbose_name='Family name',
        blank=False,
    )

    email = models.EmailField(
        verbose_name='Email address',
        blank=False,
    )

    occupation = models.CharField(
        max_length=STR_MED,
        choices=ProfileUpdateRequest.OCCUPATION_CHOICES,
        verbose_name='What is your current occupation/career stage?',
        help_text='Please choose the one that best describes you.',
        null=False, blank=True, default='undisclosed',
    )
    occupation_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other occupation/career stage',
        blank=True, default='',
    )

    affiliation = models.CharField(
        max_length=STR_LONG,
        verbose_name='Institutional Affiliation',
        null=False, blank=False,
    )

    location = models.CharField(
        max_length=STR_LONG,
        verbose_name='Location',
        help_text='please give city, province or state',
        blank=False,
    )
    country = CountryField()

    domains = models.ManyToManyField(
        'KnowledgeDomain',
        verbose_name='Areas of expertise',
        help_text='Please check all that apply.',
        limit_choices_to=~Q(name__startswith='Don\'t know yet'),
        blank=True,
    )
    domains_other = models.CharField(
        max_length=255,
        verbose_name='Other areas of expertise',
        blank=True, default='',
    )

    gender = models.CharField(
        max_length=1,
        choices=ProfileUpdateRequest.GENDER_CHOICES,
        null=False, blank=False, default=Person.UNDISCLOSED,
    )
    gender_other = models.CharField(
        max_length=STR_LONG,
        verbose_name=' ',
        blank=True, default='',
    )

    previous_involvement = models.ManyToManyField(
        'Role',
        verbose_name='Previous involvement with Software Carpentry or Data Carpentry',
        help_text='Please check all that apply.',
        blank=True,
    )

    PREVIOUS_TRAINING_CHOICES = (
        ('none', 'None'),
        ('hours', 'A few hours'),
        ('days', 'A few days'),
        ('full', 'A full degree'),
        ('other', 'Other (enter below)')
    )
    previous_training, previous_training_other = build_choice_field_with_other_option(
        choices=PREVIOUS_TRAINING_CHOICES,
        verbose_name='Previous training in teaching',
        default='none',
    )

    PREVIOUS_EXPERIENCE_CHOICES = (
        ('none', 'None'),
        ('hours', 'Have taught for a few hours'),
        ('courses', 'Have taught entire courses'),
        ('other', 'Other (enter below)')
    )
    previous_experience, previous_experience_other = build_choice_field_with_other_option(
        choices=PREVIOUS_EXPERIENCE_CHOICES,
        default='none',
        verbose_name='Previous experience in teaching'
    )

    PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES = (
        ('all-time', 'Every waking moment'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('not-much', 'Not much'),
    )
    programming_language_usage_frequency = models.CharField(
        max_length=STR_MED,
        choices=PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES,
        verbose_name='How frequently do you use Python, R or Matlab?',
        null=False, blank=False, default='all-time',
    )

    reason = models.TextField(
        verbose_name='Why do you want to attend this training course?',
        null=False, blank=False,
    )

    TEACHING_FREQUENCY_EXPECTATION_CHOICES = (
        ('not-at-all', 'Not at all'),
        ('yearly', 'Once a year'),
        ('monthly', 'Several times a year'),
        ('often', 'Primary occupation'),
        ('other', 'Other (enter below)'),
    )
    teaching_frequency_expectation, teaching_frequency_expectation_other = build_choice_field_with_other_option(
        choices=TEACHING_FREQUENCY_EXPECTATION_CHOICES,
        verbose_name='How often would you expect to teach classes on Software '
                     'or Data Carpentry Workshops after this training?',
        default='not-at-all',
    )

    MAX_TRAVELLING_FREQUENCY_CHOICES = (
        ('not-at-all', 'Not at all'),
        ('yearly', 'Once a year'),
        ('often', 'Several times a year'),
        ('other', 'Other (enter below)'),
    )
    max_travelling_frequency, max_travelling_frequency_other = build_choice_field_with_other_option(
        choices=MAX_TRAVELLING_FREQUENCY_CHOICES,
        verbose_name='How frequently would you be able to travel to teach such classes?',
        default='not-at-all',
    )

    additional_skills = models.TextField(
        verbose_name='Do you have any additional relevant skills '
                     'or interests that we should know about?',
        null=False, blank=True, default='',
    )
