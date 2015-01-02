import datetime
from django.db import models
from django.core.urlresolvers import reverse
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
    notes      = models.TextField(default="")

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
        return self.iata

    def get_absolute_url(self):
        return reverse('airport_details', args=[str(self.iata)])

#------------------------------------------------------------

# Define custom queries on the QuerySet and the Manager
class PersonQuerySet(models.query.QuerySet):
    """Handles finding past, ongoing and upcoming events"""

    def have_skills(self, skills):
        """Returns persons who have all the skills listed
        in skills, which must be a list of Skill objects.
        """

        for s in skills:
            self = self.filter(qualification__skill=s)

        return self

class PersonManager(models.Manager):
    """A custom manager which is essentially a proxy for PersonQuerySet"""

    # Attach our custom query set to the manager
    def get_queryset(self):
        return PersonQuerySet(self.model, using=self._db)

    # Proxy methods so we can call our custom filters from the manager
    # without explicitly creating an PersonQuerySet first

    def have_skills(self, skills):
        return self.get_queryset().have_skills(skills)

class Person(models.Model):
    '''Represent a single person.'''
    MALE = 'M'
    FEMALE = 'F'
    OTHER = 'O'
    GENDER_CHOICES = (
        (MALE, 'Male'),
        (FEMALE, 'Female'),
        (OTHER, 'Other'),
        )

    personal   = models.CharField(max_length=STR_LONG)
    middle     = models.CharField(max_length=STR_LONG, null=True)
    family     = models.CharField(max_length=STR_LONG)
    email      = models.CharField(max_length=STR_LONG, unique=True, null=True)
    gender     = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    active     = models.NullBooleanField()
    airport    = models.ForeignKey(Airport, null=True)
    github     = models.CharField(max_length=STR_MED, unique=True, null=True)
    twitter    = models.CharField(max_length=STR_MED, unique=True, null=True)
    url        = models.CharField(max_length=STR_LONG, null=True)
    slug       = models.CharField(max_length=STR_LONG, null=True)

    # Set the custom manager
    objects = PersonManager()

    def fullname(self):
        middle = ''
        if self.middle is not None:
            middle = ' {0}'.format(self.middle)
        return '{0}{1} {2}'.format(self.personal, middle, self.family)

    def __str__(self):
        email = ''
        if self.email is not None:
            email = ' <{0}>'.format(self.email)
        return '{0}{1}'.format(self.fullname(), email)

    def get_absolute_url(self):
        return reverse('person_details', args=[str(self.id)])

#------------------------------------------------------------

class Project(models.Model):
    '''Keep track of the kinds of project we support.'''

    slug       = models.CharField(max_length=STR_SHORT, unique=True)
    name       = models.CharField(max_length=STR_MED, unique=True)
    details    = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.slug

#------------------------------------------------------------

# In order to make our custom filters chainable, we have to
# define them on the QuerySet, not the Manager - see
# http://www.dabapps.com/blog/higher-level-query-api-django-orm/
class EventQuerySet(models.query.QuerySet):
    """Handles finding past, ongoing and upcoming events"""

    def past_events(self):
        """Return a queryset for all past events.

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

    def upcoming_events(self):
        """Return a queryset for all upcoming events.

        Upcoming events are those which start after today.
        """

        # All events that start after today
        queryset = self.filter(start__gt=datetime.date.today())

        return queryset

    def ongoing_events(self):
        """Return a queryset for all ongoing events.

        Ongoing events are those which start after today.
        """

        # All events that start before or on today
        queryset = self.filter(start__lte=datetime.date.today())

        # Of those, only the ones that finish after or on today
        queryset = queryset.filter(end__gte=datetime.date.today())

        return queryset


class EventManager(models.Manager):
    """A custom manager which is essentially a proxy for EventQuerySet"""

    # Attach our custom query set to the manager
    def get_queryset(self):
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

class Event(models.Model):
    '''Represent a single event.'''

    site       = models.ForeignKey(Site)
    project    = models.ForeignKey(Project)
    organizer  = models.ForeignKey(Site, related_name='organizer', null=True)
    start      = models.DateField()
    end        = models.DateField(null=True)
    slug       = models.CharField(max_length=STR_LONG, unique=True)
    url        = models.CharField(max_length=STR_LONG, unique=True, null=True)
    reg_key    = models.CharField(max_length=STR_REG_KEY, null=True)
    attendance = models.IntegerField(null=True)
    admin_fee  = models.DecimalField(max_digits=6, decimal_places=2)
    notes      = models.TextField(default="")

    # Set the custom manager
    objects = EventManager()

    def __str__(self):
        return self.slug

    def get_absolute_url(self):
        return reverse('event_details', args=[str(self.slug)])

#------------------------------------------------------------

class Role(models.Model):
    '''Enumerate roles in workshops.'''

    name       = models.CharField(max_length=STR_MED)

    def __str__(self):
        return self.name

#------------------------------------------------------------

class Task(models.Model):
    '''Represent who did what at events.'''

    event      = models.ForeignKey(Event)
    person     = models.ForeignKey(Person)
    role       = models.ForeignKey(Role)

    def __str__(self):
        return '{0}/{1}={2}'.format(self.event, self.person, self.role)

    def get_absolute_url(self):
        return reverse('task_details', kwargs={'event_slug':str(self.event),
                                               'person_id':self.person.pk,
                                               'role_name':str(self.role)})

#------------------------------------------------------------

class Cohort(models.Model):
    '''Represent a training cohort.'''

    start      = models.DateField()
    name       = models.CharField(max_length=STR_MED)
    active     = models.BooleanField(default=True)
    venue      = models.ForeignKey(Site, null=True) # null for online
    qualifies  = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('cohort_details', args=[str(self.name)])

#------------------------------------------------------------

class TraineeStatus(models.Model):
    '''Enumerate states that a trainee can be in.'''

    name       = models.CharField(max_length=STR_MED)

    def __str__(self):
        return self.name

#------------------------------------------------------------

class Trainee(models.Model):
    '''Represent someone taking the instructor training course.'''

    person     = models.ForeignKey(Person)
    cohort     = models.ForeignKey(Cohort)
    status     = models.ForeignKey(TraineeStatus)

    def __str__(self):
        return '{0}/{1}: {2}'.format(self.person, self.cohort, self.status.name)

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

    def __str__(self):
        return '{0}/{1}/{2}'.format(self.person, self.badge, self.awarded)
