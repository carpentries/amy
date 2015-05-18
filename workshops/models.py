import datetime
import re

from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q

#------------------------------------------------------------

STR_SHORT   =  10         # length of short strings
STR_MED     =  40         # length of medium strings
STR_LONG    = 100         # length of long strings
STR_REG_KEY =  20         # length of Eventbrite registration key

#------------------------------------------------------------

class Site(models.Model):
    '''Represent a site where workshops are hosted.'''

    domain     = models.CharField(max_length=STR_LONG, unique=True)
    fullname   = models.CharField(max_length=STR_LONG, unique=True)
    country    = models.CharField(max_length=STR_LONG, null=True)
    notes      = models.TextField(default="", blank=True)

    def __str__(self):
        return self.domain

    def get_absolute_url(self):
        return reverse('site_details', args=[str(self.domain)])

#------------------------------------------------------------

class Airport(models.Model):
    '''Represent an airport (used to locate instructors).'''

    iata      = models.CharField(max_length=STR_SHORT, unique=True)
    fullname  = models.CharField(max_length=STR_LONG, unique=True)
    country   = models.CharField(max_length=STR_LONG)
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
    airport     = models.ForeignKey(Airport, null=True, blank=True)
    github      = models.CharField(max_length=STR_MED, unique=True, null=True, blank=True)
    twitter     = models.CharField(max_length=STR_MED, unique=True, null=True, blank=True)
    url         = models.CharField(max_length=STR_LONG, null=True, blank=True)
    username    = models.CharField(max_length=STR_MED, unique=True)

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
        '''Return a queryset for all past events.

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
        '''Return a queryset for all published upcoming events.

        Upcoming events are those which start after today and are published.
        '''

        queryset = self.filter(start__gt=datetime.date.today()).filter(published=True)
        return queryset

    def ongoing_events(self):
        '''Return a queryset for all ongoing events.

        Ongoing events are those which start after today.
        '''

        # All events that start before or on today
        queryset = self.filter(start__lte=datetime.date.today())

        # Of those, only the ones that finish after or on today
        queryset = queryset.filter(end__gte=datetime.date.today())

        return queryset

    def unpublished_events(self):
        '''Return a queryset for events that are not yet published.'''

        return self.filter(published=False)

    def unpaid_events(self):
        '''Return a queryset for events that owe money.

        These are events that have an admin fee, are not marked as paid, and have occurred.'''

        return self.past_events().filter(admin_fee__gt=0).exclude(fee_paid=True)

class EventManager(models.Manager):
    '''A custom manager which is essentially a proxy for EventQuerySet'''

    # Attach our custom query set to the manager
    def get_queryset(self):
        """Fetch only existing events (ie. not deleted)."""
        return EventQuerySet(self.model, using=self._db).filter(deleted=False)

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

    def unpaid_events(self):
        return self.get_queryset().unpaid_events()

class Event(models.Model):
    '''Represent a single event.'''

    published  = models.BooleanField(default=False)
    site       = models.ForeignKey(Site)
    tags       = models.ManyToManyField(Tag)
    organizer  = models.ForeignKey(Site, related_name='organizer', null=True, blank=True)
    start      = models.DateField(null=True, blank=True)
    end        = models.DateField(null=True, blank=True)
    slug       = models.CharField(max_length=STR_LONG, null=True, blank=True)
    url        = models.CharField(max_length=STR_LONG, unique=True, null=True, blank=True)
    reg_key    = models.CharField(max_length=STR_REG_KEY, null=True, blank=True)
    attendance = models.IntegerField(null=True, blank=True)
    admin_fee  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fee_paid   = models.NullBooleanField(default=False, blank=True)
    notes      = models.TextField(default="", blank=True)
    deleted = models.BooleanField(default=False)

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
    def get_queryset(self):
        """Fetch only existing tasks (ie. not deleted)."""
        return super().get_queryset().filter(deleted=False)

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
    deleted = models.BooleanField(default=False)

    objects = TaskManager()

    class Meta:
        unique_together = ("event", "person", "role")

    def __str__(self):
        return '{0}/{1}={2}'.format(self.event, self.person, self.role)

    def get_absolute_url(self):
        return reverse('task_details', kwargs={'task_id': self.id})

#------------------------------------------------------------

class Skill(models.Model):
    '''Represent a skill someone might teach.'''

    name       = models.CharField(max_length=STR_MED)

    def __str__(self):
        return self.name

#------------------------------------------------------------

class Qualification(models.Model):
    '''What is someone qualified to teach?'''

    person     = models.ForeignKey(Person)
    skill      = models.ForeignKey(Skill)

    def __str__(self):
        return '{0}/{1}'.format(self.person, self.skill)

#------------------------------------------------------------

class Badge(models.Model):
    '''Represent a badge we award.'''

    name       = models.CharField(max_length=STR_MED)
    title      = models.CharField(max_length=STR_MED)
    criteria   = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.name

#------------------------------------------------------------

class Award(models.Model):
    '''Represent a particular badge earned by a person.'''

    person     = models.ForeignKey(Person)
    badge      = models.ForeignKey(Badge)
    awarded    = models.DateField()
    event      = models.ForeignKey(Event, null=True, blank=True)

    def __str__(self):
        return '{0}/{1}/{2}/{3}'.format(self.person, self.badge, self.awarded, self.event)
