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

    class Meta:
        ordering = ('-start', )

    # Set the custom manager
    objects = EventManager()

    def __str__(self):
        return self.get_ident()

    def get_absolute_url(self):
        return reverse('event_details', args=[self.get_ident()])

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
