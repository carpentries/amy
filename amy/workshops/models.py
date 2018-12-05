import datetime
import re
from urllib.parse import urlencode

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.db.models import (
    ExpressionWrapper,
    Q, F,
    IntegerField,
    PositiveIntegerField,
    Sum, Case, When, Value,
)
from django.utils import timezone
from django.utils.functional import cached_property
from django.urls import reverse
from django_countries.fields import CountryField
from reversion import revisions as reversion
from social_django.models import UserSocialAuth

from workshops import github_auth
from workshops.fields import NullableGithubUsernameField

STR_SHORT   =  10  # length of short strings
STR_MED     =  40  # length of medium strings
STR_LONG    = 100  # length of long strings
STR_LONGEST = 255  # length of the longest strings
STR_REG_KEY =  20  # length of Eventbrite registration key

#------------------------------------------------------------


class AssignmentMixin(models.Model):
    """This abstract model acts as a mix-in, so it adds
    "assigned to admin [...]" field to any inheriting model."""
    assigned_to = models.ForeignKey('workshops.Person', null=True, blank=True,
                                    on_delete=models.SET_NULL)

    class Meta:
        abstract = True


class ActiveMixin(models.Model):
    """This mixin adds 'active' field for marking model instances as active or
    inactive (e.g. closed or in 'not have to worry about it' state)."""
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class CreatedUpdatedMixin(models.Model):
    """This mixin provides two fields for storing instance creation time and
    last update time. It's faster than checking model revisions (and they
    aren't always enabled for some models)."""
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class DataPrivacyAgreementMixin(models.Model):
    """This mixin provides a data privacy agreement. Instead of being in the
    forms only (as a additional and required input), we're switching to having
    this agreement stored in the database."""
    data_privacy_agreement = models.BooleanField(
        null=False, blank=False,
        default=False,  # for 'normal' migration purposes
        verbose_name='I have read and agree to <a href='
                     '"https://docs.carpentries.org/'
                     'topic_folders/policies/privacy.html", '
                     'target="_blank">the data privacy policy</a> '
                     'of The Carpentries.'
    )

    class Meta:
        abstract = True


class COCAgreementMixin(models.Model):
    """This mixin provides a code-of-conduct agreement. Instead of being in the
    forms only (as a additional and required input), we're switching to having
    this agreement stored in the database."""
    code_of_conduct_agreement = models.BooleanField(
        null=False, blank=False,
        default=False,  # for 'normal' migration purposes
        verbose_name='I agree to abide by The Carpentries\' <a target="_blank"'
                     'href="https://docs.carpentries.org/topic_folders'
                     '/policies/code-of-conduct.html">Code of Conduct</a>.'
    )

    class Meta:
        abstract = True


class HostResponsibilitiesMixin(models.Model):
    """This mixin provides a workshop host responsibilities checkbox."""
    host_responsibilities = models.BooleanField(
        null=False, blank=False,
        default=False,
        verbose_name='I understand <a href="https://docs.carpentries.org/'
                     'topic_folders/hosts_instructors/index.html">the '
                     'responsibilities of the workshop host</a>, including '
                     'recruiting local helpers to support the workshop '
                     '(1 helper for every 8-10 learners).'
    )

    class Meta:
        abstract = True


class EventLink(models.Model):
    """This mixin provides a one-to-one link between a model, in which it's
    used, and single Event instance."""
    event = models.OneToOneField(
        'workshops.Event', null=True, blank=True,
        verbose_name='Linked event object',
        help_text='Link to the event instance created or otherwise related to this object.',
        on_delete=models.PROTECT,
    )

    class Meta:
        abstract = True


class StateMixin(models.Model):
    """A more extensive state field - previously a boolean `active` field was
    used, with only two states. Now there's three and can be extended."""
    STATE_CHOICES = (
        ('p', 'Pending'),
        ('d', 'Discarded'),
        ('a', 'Accepted'),
    )
    state = models.CharField(max_length=1, choices=STATE_CHOICES,
                             null=False, blank=False, default='p')

    class Meta:
        abstract = True

    @cached_property
    def active(self):
        # after changing ActiveMixin to StateMixin, this should help in some
        # cases with code refactoring; will be removed later
        return self.state == 'p'

#------------------------------------------------------------


@reversion.register
class Organization(models.Model):
    '''Represent an organization, academic or business.'''

    domain     = models.CharField(max_length=STR_LONG, unique=True)
    fullname   = models.CharField(max_length=STR_LONG, unique=True)
    country    = CountryField(null=True, blank=True)
    notes      = models.TextField(default="", blank=True)

    def __str__(self):
        return "{} <{}>".format(self.fullname, self.domain)

    def get_absolute_url(self):
        return reverse('organization_details', args=[str(self.domain)])

    class Meta:
        ordering = ('domain', )


@reversion.register
class Membership(models.Model):
    """Represent a details of Organization's membership."""

    MEMBERSHIP_CHOICES = (
        ('partner', 'Partner'),
        ('affiliate', 'Affiliate'),
        ('sponsor', 'Sponsor'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
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
        max_length=STR_MED, null=False, blank=False,
        choices=CONTRIBUTION_CHOICES,
    )
    workshops_without_admin_fee_per_agreement = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Acceptable number of workshops without admin fee per "
                  "agreement duration",
    )
    self_organized_workshops_per_agreement = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Expected number of self-organized workshops per agreement "
                  "duration",
    )
    # according to Django docs, PositiveIntegerFields accept 0 as valid as well
    seats_instructor_training = models.PositiveIntegerField(
        null=False, blank=False, default=0,
        verbose_name="Instructor training seats",
        help_text="Number of seats in instructor trainings",
    )
    additional_instructor_training_seats = models.PositiveIntegerField(
        null=False, blank=False, default=0,
        verbose_name="Additional instructor training seats",
        help_text="Use this field if you want to grant more seats than "
                  "the agreement provides for.",
    )
    notes = models.TextField(default="", blank=True)
    organization = models.ForeignKey(Organization, null=False, blank=False,
                             on_delete=models.PROTECT)

    def __str__(self):
        from workshops.util import human_daterange
        dates = human_daterange(self.agreement_start, self.agreement_end)
        return "{} membership: {} ({})".format(self.variant.title(),
                                               self.organization,
                                               dates)

    def get_absolute_url(self):
        return reverse('membership_details', args=[self.id])

    @cached_property
    def workshops_without_admin_fee_completed(self):
        """Count workshops without admin fee hosted the during agreement."""
        self_organized = (Q(administrator=None) |
                          Q(administrator__domain='self-organized'))
        no_fee = Q(admin_fee=0) | Q(admin_fee=None)
        date_started = Q(start__gte=self.agreement_start, start__lt=self.agreement_end)

        return Event.objects.filter(host=self.organization) \
                            .filter(date_started) \
                            .filter(no_fee) \
                            .exclude(self_organized).count()

    @cached_property
    def workshops_without_admin_fee_remaining(self):
        """Count remaining workshops w/o admin fee for the agreement."""
        if not self.workshops_without_admin_fee_per_agreement:
            return None
        a = self.workshops_without_admin_fee_per_agreement
        b = self.workshops_without_admin_fee_completed
        return a - b

    @cached_property
    def self_organized_workshops_completed(self):
        """Count self-organized workshops hosted the year agreement started."""
        self_organized = (Q(administrator=None) |
                          Q(administrator__domain='self-organized'))
        date_started = Q(start__gte=self.agreement_start, start__lt=self.agreement_end)

        return Event.objects.filter(host=self.organization) \
                            .filter(date_started) \
                            .filter(self_organized).count()

    @cached_property
    def self_organized_workshops_remaining(self):
        """Count remaining self-organized workshops for the year agreement
        started."""
        if not self.self_organized_workshops_per_agreement:
            return None
        a = self.self_organized_workshops_per_agreement
        b = self.self_organized_workshops_completed
        return a - b

    @cached_property
    def seats_instructor_training_total(self):
        return (self.additional_instructor_training_seats +
                self.seats_instructor_training)

    @cached_property
    def seats_instructor_training_utilized(self):
        # count number of tasks that have this membership
        return self.task_set.filter(role__name="learner").count()

    @cached_property
    def seats_instructor_training_remaining(self):
        return (self.seats_instructor_training_total -
                self.seats_instructor_training_utilized)


class Sponsorship(models.Model):
    '''Represent sponsorship from a host for an event.'''

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        help_text='Organization sponsoring the event'
    )
    event = models.ForeignKey(
        'Event',
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        validators=[MinValueValidator(0)],
        verbose_name='Sponsorship amount',
        help_text='e.g. 1992.33'
    )
    contact = models.ForeignKey(
        'Person',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    class Meta:
        unique_together = ('organization', 'event', 'amount')

    def __str__(self):
        return '{}: {}'.format(self.organization, self.amount)


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

    class Meta:
        ordering = (
            'iata',
        )

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
        if isinstance(username, str) and '@' in username:
            return self.get(email=username)
        else:
            return super().get_by_natural_key(username)

    def annotate_with_instructor_eligibility(self):
        def passed(requirement):
            return Sum(Case(When(trainingprogress__requirement__name=requirement,
                                 trainingprogress__state='p',
                                 trainingprogress__discarded=False,
                                 then=1),
                            default=0,
                            output_field=IntegerField()))

        def passed_either(req_a, req_b):
            return Sum(Case(When(trainingprogress__requirement__name=req_a,
                                 trainingprogress__state='p',
                                 trainingprogress__discarded=False,
                                 then=1),
                            When(trainingprogress__requirement__name=req_b,
                                 trainingprogress__state='p',
                                 trainingprogress__discarded=False,
                                 then=1),
                            default=0,
                            output_field=IntegerField()))

        return self.annotate(
            passed_training=passed('Training'),
            passed_swc_homework=passed('SWC Homework'),
            passed_dc_homework=passed('DC Homework'),
            passed_discussion=passed('Discussion'),
            passed_swc_demo=passed('SWC Demo'),
            passed_dc_demo=passed('DC Demo'),
            passed_homework=passed_either('SWC Homework', 'DC Homework'),
            passed_demo=passed_either('SWC Demo', 'DC Demo'),
        ).annotate(
            # We're using Maths to calculate "binary" score for a person to
            # be instructor badge eligible. Legend:
            # * means "AND"
            # + means "OR"
            instructor_eligible=(
                F('passed_training') *
                (F('passed_swc_homework') + F('passed_dc_homework')) *
                F('passed_discussion') *
                (F('passed_swc_demo') + F('passed_dc_demo'))
            )
        )


@reversion.register
class Person(AbstractBaseUser, PermissionsMixin, DataPrivacyAgreementMixin):
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

    personal    = models.CharField(max_length=STR_LONG,
                                   verbose_name='Personal (first) name')
    middle      = models.CharField(max_length=STR_LONG, blank=True,
                                   verbose_name='Middle name')
    family      = models.CharField(max_length=STR_LONG, blank=True, null=True,
                                   verbose_name='Family (last) name')
    email       = models.CharField(max_length=STR_LONG, unique=True, null=True, blank=True,
                                   verbose_name='Email address')
    gender      = models.CharField(max_length=1, choices=GENDER_CHOICES, null=False, default=UNDISCLOSED)
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
    country     = CountryField(null=False, blank=True, default='', help_text='Person\'s country of residence.')
    airport     = models.ForeignKey(Airport, null=True, blank=True, on_delete=models.PROTECT,
                                    verbose_name='Nearest major airport')
    github      = NullableGithubUsernameField(unique=True, null=True, blank=True,
                                              verbose_name='GitHub username',
                                              help_text='Please put only a single username here.')
    twitter     = models.CharField(max_length=STR_MED, unique=True, null=True, blank=True,
                                   verbose_name='Twitter username')
    url         = models.CharField(max_length=STR_LONG, blank=True,
                                   verbose_name='Personal website')
    username = models.CharField(
        max_length=STR_MED, unique=True,
        validators=[RegexValidator(r'^[\w\-_]+$', flags=re.A)],
    )
    user_notes = models.TextField(
        default='', blank=True,
        verbose_name='Notes provided by the user in update profile form.')
    notes = models.TextField(default="", blank=True,
                             verbose_name='Admin notes')
    affiliation = models.CharField(
        max_length=STR_LONG, default='', blank=True,
        help_text='What university, company, lab, or other organization are '
                  'you affiliated with (if any)?')

    badges = models.ManyToManyField(
        "Badge", through="Award",
        through_fields=('person', 'badge'))
    lessons = models.ManyToManyField(
        "Lesson",
        through="Qualification",
        verbose_name='Topic and lessons you\'re comfortable teaching',
        help_text='Please check all that apply.',
        blank=True,
    )
    domains = models.ManyToManyField(
        "KnowledgeDomain",
        limit_choices_to=~Q(name__startswith='Don\'t know yet'),
        verbose_name='Areas of expertise',
        help_text='Please check all that apply.',
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

    LESSON_PUBLICATION_CHOICES = (
        ('yes-profile', 'Yes, and use the name associated with my profile'),
        ('yes-orcid',
         'Yes, and use the name associated with my ORCID profile'),
        ('yes-github', 'Yes, and only use my GitHub handle'),
        ('no', 'No'),
    )
    lesson_publication_consent = models.CharField(
        max_length=STR_MED, choices=LESSON_PUBLICATION_CHOICES,
        blank=True, default='no', null=False,
        verbose_name='Do you consent to have your name or identity associated '
                     'with lesson publications?',
        help_text='When we publish our lessons, we like to include everyone '
                  'who has contributed via pull request as an author. If you '
                  'do make any contributions, would you like to be included '
                  'as an author when we publish the lesson?',
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = [
        'personal',
        'family',
        'email',
    ]

    objects = PersonManager()

    class Meta:
        ordering = ['family', 'personal']

        # additional permissions
        permissions = [
            ('can_access_restricted_API',
             'Can this user access the restricted API endpoints?'),
        ]

    @cached_property
    def full_name(self):
        middle = ''
        if self.middle:
            middle = ' {0}'.format(self.middle)
        return '{0}{1} {2}'.format(self.personal, middle, self.family)

    def get_short_name(self):
        return self.personal

    def __str__(self):
        result = self.full_name
        if self.email:
            result += ' <' + self.email + '>'
        return result

    def get_absolute_url(self):
        return reverse('person_details', args=[str(self.id)])

    @property
    def github_usersocialauth(self):
        """List of all associated GitHub accounts with this Person. Returns
        list of UserSocialAuth."""
        return self.social_auth.filter(provider='github')

    def get_github_uid(self):
        """Return UID (int) of GitHub account for username == `Person.github`.

        Return `None` in case of errors or missing GitHub account.
        May raise ValueError in the case of IO issues."""
        if self.github and self.is_active:
            try:
                # if the username is incorrect, this will throw ValidationError
                github_auth.validate_github_username(self.github)

                github_uid = github_auth.github_username_to_uid(self.github)
            except (ValidationError, ValueError):
                github_uid = None
        else:
            github_uid = None

        return github_uid

    def synchronize_usersocialauth(self):
        """Disconnect all GitHub account associated with this Person and
        associates the account with username == `Person.github`, if there is
        such GitHub account.

        May raise GithubException in the case of IO issues."""

        github_uid = self.get_github_uid()

        if github_uid is not None:
            self.github_usersocialauth.delete()
            return UserSocialAuth.objects.create(provider='github', user=self,
                                                 uid=github_uid, extra_data={})
        else:
            return False

    @property
    def is_staff(self):
        """Required for logging into admin panel at '/admin/'."""
        return self.is_superuser

    @property
    def is_admin(self):
        return is_admin(self)

    def get_missing_swc_instructor_requirements(self):
        """Returns set of requirements' names (list of strings) that are not
        passed yet by the trainee and are mandatory to become SWC Instructor.
        """

        fields = [
            ('passed_training', 'Training'),
            ('passed_homework', 'SWC or DC Homework'),
            ('passed_discussion', 'Discussion'),
            ('passed_demo', 'SWC or DC Demo'),
        ]
        try:
            return [name for field, name in fields if not getattr(self, field)]
        except AttributeError as e:
            raise Exception('Did you forget to call '
                            'annotate_with_instructor_eligibility()?') from e

    def get_missing_dc_instructor_requirements(self):
        """Returns set of requirements' names (list of strings) that are not
        passed yet by the trainee and are mandatory to become DC Instructor."""

        fields = [
            ('passed_training', 'Training'),
            ('passed_homework', 'SWC or DC Homework'),
            ('passed_discussion', 'Discussion'),
            ('passed_demo', 'SWC or DC Demo'),
        ]
        try:
            return [name for field, name in fields if not getattr(self, field)]
        except AttributeError as e:
            raise Exception('Did you forget to call '
                            'annotate_with_instructor_eligibility()?') from e

    def get_training_tasks(self):
        """Returns Tasks related to Instuctor Training events at which this
        person was trained."""
        return Task.objects.filter(person=self,
                                   role__name='learner',
                                   event__tags__name='TTT')

    def clean(self):
        """This will be called by the ModelForm.is_valid(). No saving to the
        database."""
        # lowercase the email
        self.email = self.email.lower() if self.email else None

    def save(self, *args, **kwargs):
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
        self.gender = self.gender or None
        self.airport = self.airport or None
        self.github = self.github or None
        self.twitter = self.twitter or None
        super().save(*args, **kwargs)


def is_admin(user):
    if user is None or user.is_anonymous:
        return False
    else:
        return (user.is_superuser or
                user.groups.filter(Q(name='administrators') |
                                   Q(name='steering committee') |
                                   Q(name='invoicing') |
                                   Q(name='trainers')).exists())


#------------------------------------------------------------

class TagQuerySet(models.query.QuerySet):
    def main_tags(self):
        names = ['SWC', 'DC', 'LC', 'TTT', 'ITT', 'WiSE']
        return Tag.objects.filter(name__in=names).order_by('id')

    def carpentries(self):
        return Tag.objects.filter(name__in=['SWC', 'DC', 'LC']).order_by('id')


class Tag(models.Model):
    '''Label for grouping events.'''

    ITEMS_VISIBLE_IN_SELECT_WIDGET = 13

    name       = models.CharField(max_length=STR_MED, unique=True)
    details    = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.name

    objects = TagQuerySet.as_manager()

#------------------------------------------------------------

class Language(models.Model):
    """A language tag.

    https://tools.ietf.org/html/rfc5646
    """
    name = models.CharField(
        max_length=STR_LONG,
        help_text='Description of this language tag in English')
    subtag = models.CharField(
        max_length=STR_SHORT,
        help_text=
            'Primary language subtag.  '
            'https://tools.ietf.org/html/rfc5646#section-2.2.1')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

#------------------------------------------------------------

# In order to make our custom filters chainable, we have to
# define them on the QuerySet, not the Manager - see
# http://www.dabapps.com/blog/higher-level-query-api-django-orm/
class EventQuerySet(models.query.QuerySet):
    '''Handles finding past, ongoing and upcoming events'''

    def not_cancelled(self):
        """Exclude cancelled events."""
        return self.exclude(tags__name='cancelled')

    def not_unresponsive(self):
        """Exclude unresponsive events."""
        return self.exclude(tags__name='unresponsive')

    def active(self):
        """Exclude inactive events (stalled, completed, cancelled or
        unresponsive)."""
        return self.exclude(tags__name='stalled').exclude(completed=True) \
                   .not_cancelled().not_unresponsive()

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
        url OR are marked as 'cancelled' (ie. unpublished events). This will be
        used in `self.published_events`, too."""
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
        """Return active events considered as unpublished (see
        `unpublished_conditional` above)."""
        conditional = self.unpublished_conditional()
        return self.active().filter(conditional) \
                   .order_by('slug', 'id').distinct()

    def published_events(self):
        """Return events considered as published (see `unpublished_conditional`
        above)."""
        conditional = self.unpublished_conditional()
        return self.not_cancelled().exclude(conditional) \
                   .order_by('-start', 'id').distinct()

    def uninvoiced_events(self):
        '''Return a queryset for events that have not yet been invoiced.

        These are marked as uninvoiced, and have occurred.
        Events are sorted oldest first.'''

        return self.not_cancelled().past_events() \
                   .filter(invoice_status='not-invoiced') \
                   .order_by('start')

    def metadata_changed(self):
        """Return events for which remote metatags have been updated."""
        return self.filter(metadata_changed=True)

    def ttt(self):
        """Return only TTT events."""
        return self.filter(tags__name='TTT').distinct()


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

    host = models.ForeignKey(Organization, on_delete=models.PROTECT,
                             help_text='Organization hosting the event.')
    tags = models.ManyToManyField(
        Tag,
        help_text='<ul><li><i>stalled</i> — for events with lost contact with '
                  'the host or TTT events that aren\'t running.</li>'
                  '<li><i>unresponsive</i> – for events whose hosts and/or '
                  'organizers aren\'t going to send us attendance data.</li>'
                  '<li><i>cancelled</i> — for events that were supposed to '
                  'happen, but due to some circumstances got cancelled.</li>'
                  '</ul>',
    )
    administrator = models.ForeignKey(
        Organization, related_name='administrator', null=True, blank=True,
        on_delete=models.PROTECT,
        help_text='Organization responsible for administrative work.'
    )
    sponsors = models.ManyToManyField(
        Organization, related_name='sponsored_events', blank=True,
        through=Sponsorship,
    )
    start = models.DateField(
        null=True, blank=True,
        help_text=PUBLISHED_HELP_TEXT,
    )
    end = models.DateField(
        null=True, blank=True,
    )
    slug = models.SlugField(
        max_length=STR_LONG, unique=True,
        help_text='Use <code>YYYY-MM-DD-location</code> format, where '
                  '<code>location</code> is either an organization, or city, '
                  'or both. If the specific date is unknown, use '
                  '<code>xx</code> instead, for example: <code>2016-12-xx'
                  '-Krakow</code> means that the event is supposed to run '
                  'sometime in December 2016 in Kraków. Use only latin '
                  'characters.',
    )
    language = models.ForeignKey(
        Language, on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text='Human language of instruction during the workshop.'
    )
    url = models.CharField(
        max_length=STR_LONG, unique=True, null=True, blank=True,
        validators=[RegexValidator(REPO_REGEX, inverse_match=True)],
        help_text=PUBLISHED_HELP_TEXT +
                  '<br />Use link to the event\'s <b>website</b>, ' +
                  'not repository.',
        verbose_name='URL',
    )
    reg_key    = models.CharField(max_length=STR_REG_KEY, blank=True, verbose_name="Eventbrite key")
    attendance = models.PositiveIntegerField(null=True, blank=True)
    admin_fee  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    INVOICED_CHOICES = (
        ('unknown', 'Unknown'),
        ('invoiced', 'Invoice requested'),
        ('not-invoiced', 'Invoice not requested'),
        ('na-historic', 'Not applicable for historical reasons'),
        ('na-member', 'Not applicable because of membership'),
        ('na-self-org', 'Not applicable because self-organized'),
        ('na-waiver', 'Not applicable because waiver granted'),
        ('na-other', 'Not applicable because other arrangements made'),
        ('paid', 'Paid'),
    )
    invoice_status = models.CharField(
        max_length=STR_MED,
        choices=INVOICED_CHOICES,
        verbose_name='Invoice status',
        default='not-invoiced', blank=False,
    )
    notes      = models.TextField(default="", blank=True)
    contact = models.CharField(max_length=STR_LONGEST, default="", blank=True)
    country = CountryField(
        null=True, blank=True,
        help_text=PUBLISHED_HELP_TEXT +
                  '<br />Use <b>Online</b> for online events.',
    )
    venue = models.CharField(
        max_length=STR_LONGEST, default='', blank=True,
        help_text=PUBLISHED_HELP_TEXT,
    )
    address = models.CharField(
        max_length=STR_LONGEST, default='', blank=True,
        help_text=PUBLISHED_HELP_TEXT,
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

    # defines if people not associated with specific member sites can take part
    # in TTT event
    open_TTT_applications = models.BooleanField(
        null=False, blank=True, default=False,
        verbose_name="TTT Open applications",
        help_text="If this event is <b>TTT</b>, you can mark it as 'open "
                  "applications' which means that people not associated with "
                  "this event's member sites can also take part in this event."
    )

    # taught curriculum information
    curricula = models.ManyToManyField(
        "Curriculum",
        blank=True,
        limit_choices_to={'active': True, 'unknown': False},
        verbose_name="Curricula taught at the workshop",
    )

    class Meta:
        ordering = ('-start', )

    # make a custom manager from our QuerySet derivative
    objects = EventQuerySet.as_manager()

    def __str__(self):
        return self.slug

    def get_absolute_url(self):
        return reverse('event_details', args=[self.slug])

    @cached_property
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

    @cached_property
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

    @cached_property
    def uninvoiced(self):
        """Indicate if the event has been invoiced or not."""
        return self.invoice_status == 'not-invoiced'

    @cached_property
    def contacts(self):
        return (
            self.task_set
                .filter(
                    # we only want hosts, organizers and instructors
                    Q(role__name='host') | Q(role__name='organizer') |
                    Q(role__name='instructor')
                )
                .filter(person__may_contact=True)
                .exclude(Q(person__email='') | Q(person__email=None))
                .values_list('person__email', flat=True)
        )

    @cached_property
    def mailto(self):
        """Return list of emails we can contact about workshop details, like
        attendance."""
        from workshops.util import find_emails

        emails = find_emails(self.contact)
        return emails

    def get_invoice_form_url(self):
        from workshops.util import universal_date_format

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
        from workshops.util import human_daterange
        date1 = self.start
        date2 = self.end
        return human_daterange(date1, date2)

    def clean(self):
        """Additional model validation."""

        # Applies only to saved model instances!!! Otherwise it's impossible
        # to access M2M objects.
        if self.pk:
            errors = dict()
            has_TTT = self.tags.filter(name='TTT')

            if self.open_TTT_applications and not has_TTT:
                errors['open_TTT_applications'] = (
                    'You cannot open applications on non-TTT event.'
                )

            if errors:
                raise ValidationError(errors)
        # additional validation before the object is saved is in EventForm

    def save(self, *args, **kwargs):
        self.slug = self.slug or None
        self.url = self.url or None

        if self.country == 'W3':
            # enforce location data for 'Online' country
            self.venue = 'Internet'
            self.address = 'Internet'
            self.latitude = -48.876667
            self.longitude = -123.393333

        # Increase attendance if there's more learner tasks
        learners = self.task_set.filter(role__name='learner').count()
        if learners != 0:
            if not self.attendance or self.attendance < learners:
                self.attendance = learners

        super(Event, self).save(*args, **kwargs)


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

    event      = models.ForeignKey(Event, on_delete=models.PROTECT)
    person     = models.ForeignKey(Person, on_delete=models.PROTECT)
    role       = models.ForeignKey(Role, on_delete=models.PROTECT)
    title      = models.CharField(max_length=STR_LONG, blank=True)
    url        = models.URLField(blank=True, verbose_name='URL')
    seat_membership = models.ForeignKey(
        Membership, on_delete=models.PROTECT, null=True, blank=True,
        default=None, verbose_name="Associated member site in TTT event",
        help_text="In order to count this person into number of used "
                  "membership instructor training seats, a correct membership "
                  "entry needs to be selected.",
    )
    seat_open_training = models.BooleanField(
        null=False, blank=True, default=False,
        verbose_name="Open training seat",
        help_text="Some TTT events allow for open training; check this field "
                  "to count this person into open applications."
    )

    objects = TaskManager()

    class Meta:
        unique_together = ('event', 'person', 'role', 'url')
        ordering = ("role__name", "event")

    def __str__(self):
        if self.title:
            return self.title
        return '{0}/{1}={2}'.format(self.event, self.person, self.role)

    def get_absolute_url(self):
        return reverse('task_details', kwargs={'task_id': self.id})

    def clean(self):
        """Additional model validation."""

        # check seats, make sure the corresponding event has "TTT" tag
        errors = dict()
        has_ttt = bool(self.event.tags.filter(name="TTT"))
        is_open_app = self.event.open_TTT_applications

        if self.seat_membership is not None and self.seat_open_training:
            raise ValidationError(
                "This Task cannot be simultaneously open training and use "
                "a Membership instructor training seat."
            )

        if not has_ttt and self.seat_membership is not None:
            errors['seat_membership'] = ValidationError(
                "Cannot associate membership when the event has no TTT tag",
                code='invalid',
            )

        if not has_ttt and self.seat_open_training:
            errors['seat_open_training'] = ValidationError(
                "Cannot mark this person as open applicant, because the event "
                "has no TTT tag.",
                code='invalid',
            )
        elif has_ttt and not is_open_app and self.seat_open_training:
            errors['seat_open_training'] = ValidationError(
                "Cannot mark this person as open applicant, because the TTT "
                "event is not marked as open applications.",
                code='invalid',
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Trigger an update of the attendance field
        self.event.save()

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

    person     = models.ForeignKey(Person, on_delete=models.PROTECT)
    lesson     = models.ForeignKey(Lesson, on_delete=models.PROTECT)

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

    # just for easier access outside `models.py`
    INSTRUCTOR_BADGES = BadgeQuerySet.INSTRUCTOR_BADGES

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

    person     = models.ForeignKey(Person, on_delete=models.PROTECT)
    badge      = models.ForeignKey(Badge, on_delete=models.PROTECT)
    awarded    = models.DateField(default=datetime.date.today)
    event      = models.ForeignKey(Event, null=True, blank=True,
                                   on_delete=models.PROTECT)
    awarded_by = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT,
        related_name='awarded_set')

    class Meta:
        unique_together = ("person", "badge", )
        ordering = ['awarded']

    def __str__(self):
        return '{0}/{1}/{2}/{3}'.format(self.person, self.badge, self.awarded, self.event)

#------------------------------------------------------------

class KnowledgeDomain(models.Model):
    """Represent a knowledge domain a person is engaged in."""
    name = models.CharField(max_length=STR_LONG)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# ------------------------------------------------------------


@reversion.register
class InvoiceRequest(models.Model):
    STATUS_CHOICES = (
        ('not-invoiced', 'Invoice not requested'),
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
        Organization, on_delete=models.PROTECT, verbose_name='Organization to invoice',
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

from workshops.util import build_choice_field_with_other_option


class TrainingRequestManager(models.Manager):
    def get_queryset(self):
        """Enhance default TrainingRequest queryset with auto-computed
        fields."""
        return super().get_queryset().annotate(
            score_total=Case(
                When(score_manual__isnull=False,
                     then=F('score_auto') + F('score_manual')),
                When(score_manual__isnull=True,
                     then=F('score_auto')),
                output_field=PositiveIntegerField(),
            ),
        )


@reversion.register
class TrainingRequest(CreatedUpdatedMixin,
        DataPrivacyAgreementMixin, COCAgreementMixin, StateMixin,
        models.Model):

    MANUAL_SCORE_UPLOAD_FIELDS = (
        'request_id', 'score_manual', 'score_notes',
    )

    person = models.ForeignKey(Person, null=True, blank=True,
                               verbose_name='Matched Trainee',
                               on_delete=models.SET_NULL)

    # no association with Event

    group_name = models.CharField(
        blank=True, default='', null=False,
        max_length=STR_LONG,
        verbose_name='Group name',
        help_text='If you are scheduled to receive training at a member site, '
                  'please enter the group name you were provided. Otherwise '
                  'please leave this blank.',
    )

    personal = models.CharField(
        max_length=STR_LONG,
        verbose_name='Personal (given) name',
        blank=False,
    )
    middle = models.CharField(
        max_length=STR_LONG,
        verbose_name='Middle name',
        blank=True,
    )
    family = models.CharField(
        max_length=STR_LONG,
        verbose_name='Family name (surname)',
        blank=False,
    )

    email = models.EmailField(
        verbose_name='Email address',
        blank=False,
    )
    github = NullableGithubUsernameField(
        verbose_name='GitHub username',
        help_text='Please put only a single username here.',
        null=True, blank=True,
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
        ('', 'Other:'),
    )
    occupation = models.CharField(
        max_length=STR_MED,
        choices=OCCUPATION_CHOICES,
        verbose_name='What is your current occupation/career stage?',
        help_text='Please choose the one that best describes you.',
        blank=True, default='undisclosed',
    )
    occupation_other = models.CharField(
        max_length=STR_LONG,
        verbose_name='Other occupation/career stage',
        blank=True, default='',
    )

    affiliation = models.CharField(
        max_length=STR_LONG,
        verbose_name='Affiliation',
        null=False, blank=False,
    )

    location = models.CharField(
        max_length=STR_LONG,
        verbose_name='Location',
        help_text='Please give city, and province or state if applicable. Do '
                  'not share a full mailing address.',
        blank=False,
    )
    country = CountryField()
    underresourced = models.BooleanField(
        null=False, default=False, blank=True,
        verbose_name='This is a small, remote, or under-resourced institution',
        help_text='The Carpentries strive to make workshops accessible to as '
                  'many people as possible, in as wide a variety of situations'
                  ' as possible.'
    )

    domains = models.ManyToManyField(
        'KnowledgeDomain',
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

    # a single checkbox for under-represented minorities
    # instead of two "gender" fields
    underrepresented = models.CharField(
        max_length=STR_LONGEST, blank=True, null=True,
        verbose_name='I self-identify as a member of a group that is '
                     'under-represented in research and/or computing, e.g., '
                     'women, ethnic minorities, LGBTQ, etc.',
        help_text="Provide details or leave blank if this doesn't apply"
                  " to you."
    )

    # new field for teaching-related experience in non-profit or volunteer org.
    nonprofit_teaching_experience = models.CharField(
        max_length=STR_LONGEST, blank=True, null=True,
        verbose_name='I have been an active contributor to other volunteer or'
                     ' non-profit groups with significant teaching or training'
                     ' components.',
        help_text="Provide details or leave blank if this doesn't apply"
                  " to you."
    )

    previous_involvement = models.ManyToManyField(
        'Role',
        verbose_name='In which of the following ways have you been involved with The Carpentries',
        help_text='Please check all that apply.',
        blank=True,
    )

    PREVIOUS_TRAINING_CHOICES = (
        ('none', 'None'),
        ('hours', 'A few hours'),
        ('workshop', 'A workshop'),
        ('course', 'A certification or short course'),
        ('full', 'A full degree'),
        ('other', 'Other:')
    )
    previous_training, previous_training_other = build_choice_field_with_other_option(
        choices=PREVIOUS_TRAINING_CHOICES,
        verbose_name='Previous formal training as a teacher or instructor',
        default='none',
    )
    previous_training_explanation = models.TextField(
        verbose_name='Description of your previous training in teaching',
        null=True, blank=True,
    )

    # this part changed a little bit, mostly wording and choices
    PREVIOUS_EXPERIENCE_CHOICES = (
        ('none', 'None'),
        ('hours', 'A few hours'),
        ('workshop', 'A workshop (full day or longer)'),
        ('ta', 'Teaching assistant for a full course'),
        ('courses', 'Primary instructor for a full course'),
        ('other', 'Other:')
    )
    previous_experience, previous_experience_other = build_choice_field_with_other_option(
        choices=PREVIOUS_EXPERIENCE_CHOICES,
        default='none',
        verbose_name='Previous experience in teaching',
        help_text='Please include teaching experience at any level from grade '
                  'school to post-secondary education.'
    )
    previous_experience_explanation = models.TextField(
        verbose_name='Description of your previous experience in teaching',
        null=True, blank=True,
    )

    PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES = (
        ('daily', 'Every day'),
        ('weekly', 'A few times a week'),
        ('monthly', 'A few times a month'),
        ('yearly', 'A few times a year'),
        ('not-much', 'Never or almost never'),
    )
    programming_language_usage_frequency = models.CharField(
        max_length=STR_MED,
        choices=PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES,
        verbose_name='How frequently do you work with the tools that The '
                     'Carpentries teach, such as R, Python, MATLAB, Perl, '
                     'SQL, Git, OpenRefine, and the Unix Shell?',
        null=False, blank=False, default='daily',
    )

    TEACHING_FREQUENCY_EXPECTATION_CHOICES = (
        ('not-at-all', 'Not at all'),
        ('yearly', 'Once a year'),
        ('monthly', 'Several times a year'),
        ('other', 'Other:'),
    )
    teaching_frequency_expectation, teaching_frequency_expectation_other = build_choice_field_with_other_option(
        choices=TEACHING_FREQUENCY_EXPECTATION_CHOICES,
        verbose_name='How often would you expect to teach Carpentry Workshops'
                     ' after this training?',
        default='not-at-all',
    )

    MAX_TRAVELLING_FREQUENCY_CHOICES = (
        ('not-at-all', 'Not at all'),
        ('yearly', 'Once a year'),
        ('often', 'Several times a year'),
        ('other', 'Other:'),
    )
    max_travelling_frequency, max_travelling_frequency_other = build_choice_field_with_other_option(
        choices=MAX_TRAVELLING_FREQUENCY_CHOICES,
        verbose_name='How frequently would you be able to travel to teach such classes?',
        default='not-at-all',
    )

    reason = models.TextField(
        verbose_name='Why do you want to attend this training course?',
        null=False, blank=False,
    )

    comment = models.TextField(
        default='', null=False, blank=True,
        help_text='What else do you want us to know?',
        verbose_name='Anything else?')

    # a few agreements
    training_completion_agreement = models.BooleanField(
        null=False, blank=False,
        default=False,  # for 'normal' migration purposes
        verbose_name='I agree to complete this training within three months of'
                     ' the training course. The completion steps are described'
                     ' at <a href="http://carpentries.github.io/instructor-'
                     'training/checkout/">http://carpentries.github.io/'
                     'instructor-training/checkout/</a>.'
    )
    workshop_teaching_agreement = models.BooleanField(
        null=False, blank=False,
        default=False,  # for 'normal' migration purposes
        verbose_name='I agree to teach a Carpentry workshop within 12 months '
                     'of this Training Course.'
    )

    notes = models.TextField(blank=True, help_text='Admin notes')

    score_auto = models.PositiveIntegerField(
        null=False, blank=False, default=0,
        verbose_name="Application automatic score",
        help_text="Filled out by AMY.",
    )
    score_manual = models.IntegerField(
        null=True, blank=True,
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
        ordering = ['created_at']

    def clean(self):
        super().clean()

        if self.state == 'p' and self.person is not None \
                and self.person.get_training_tasks().exists():
            raise ValidationError({'state': 'Pending training request cannot '
                                            'be matched with a training.'})

    def recalculate_score_auto(self):
        """Calculate automatic score according to the rubric:
        https://github.com/carpentries/instructor-training/blob/gh-pages/files/rubric.md"""
        score = 0

        # location based points (country not on the list of countries)
        # according to
        # https://github.com/swcarpentry/amy/issues/1327#issuecomment-422539917
        # and
        # https://github.com/swcarpentry/amy/issues/1327#issuecomment-423292177
        not_scoring_countries = [
            'US', 'CA', 'NZ', 'GB', 'AU', 'AT', 'BE', 'CY', 'CZ',
            'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT',
            'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE',
            'CH', 'IS', 'NO',
        ]
        if self.country and self.country.code not in not_scoring_countries:
            score += 1

        if self.underresourced:
            score += 1

        # economics or social sciences, arts, humanities, or library science
        scoring_domains = [
            'Humanities', 'Library and information science',
            'Economics/business', 'Social sciences',
        ]
        for domain in self.domains.all():
            if domain.name in scoring_domains:
                score += 1
                break

        # +1 for each previous involvement with The Carpentries (max. 3)
        prev_inv_count = len(self.previous_involvement.all())
        score += prev_inv_count if prev_inv_count <= 3 else 3

        # previous training in teaching: "a certification or short course"
        # or "a full degree"
        if self.previous_training in ['course', 'full']:
            score += 1

        # previous experience in teaching: "TA for full course"
        # or "primary instructor for full course"
        if self.previous_experience in ['ta', 'courses']:
            score += 1

        # using tools "every day" or "a few times a week"
        if self.programming_language_usage_frequency in ['daily', 'weekly']:
            score += 1

        return score

    def save(self, *args, **kwargs):
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
        if inserted and 'force_insert' in kwargs:
            kwargs.pop('force_insert')

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('trainingrequest_details', args=[self.pk])

    def __str__(self):
        return (
            '{personal} {family} <{email}> - {state}'
            .format(
                state=self.get_state_display(),
                personal=self.personal,
                family=self.family,
                email=self.email,
                timestamp=self.created_at,
            )
        )

    def get_underrepresented_display(self):
        if self.underrepresented:
            return "Yes: {}".format(self.underrepresented)
        else:
            return "No"


@reversion.register
class TrainingRequirement(models.Model):
    name = models.CharField(max_length=STR_MED)

    # Determines whether TrainingProgress.url is required (True) or must be
    # null (False).
    url_required = models.BooleanField(default=False)

    # Determines whether TrainingProgress.event is required (True) or must be
    # null (False).
    event_required = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@reversion.register
class TrainingProgress(CreatedUpdatedMixin, models.Model):
    trainee = models.ForeignKey(Person, on_delete=models.PROTECT)

    # Mentor/examiner who evaluates homework / session. May be null when a
    # trainee submits their homework.
    evaluated_by = models.ForeignKey(Person,
                                     on_delete=models.PROTECT,
                                     null=True, blank=True,
                                     related_name='+')
    requirement = models.ForeignKey(TrainingRequirement,
                                    on_delete=models.PROTECT,
                                    verbose_name='Type')

    STATES = (
        ('n', 'Not evaluated yet'),
        ('f', 'Failed'),
        ('p', 'Passed'),
    )
    state = models.CharField(choices=STATES, default='p', max_length=1)

    # When we end training and trainee has gone silent, or passed their
    # deadline, we set this field to True.
    discarded = models.BooleanField(
        default=False,
        verbose_name='Discarded',
        help_text='Check when the trainee has gone silent or passed their '
                  'training deadline. Discarded items are not permanently '
                  'deleted permanently from AMY. If you want to remove this '
                  'record, click red "delete" button.')

    event = models.ForeignKey(Event, null=True, blank=True,
                              verbose_name='Training',
                              limit_choices_to=Q(tags__name='TTT'),
                              on_delete=models.SET_NULL)
    url = models.URLField(null=True, blank=True, verbose_name='URL')
    notes = models.TextField(blank=True)

    def get_absolute_url(self):
        return reverse('trainingprogress_edit', args=[str(self.id)])

    def clean(self):
        if self.requirement.url_required and not self.url:
            msg = 'In the case of {}, this field is required.'.format(self.requirement)
            raise ValidationError({'url': msg})
        elif not self.requirement.url_required and self.url:
            msg = 'In the case of {}, this field must be left empty.'.format(self.requirement)
            raise ValidationError({'url': msg})

        if self.requirement.event_required and not self.event:
            msg = 'In the case of {}, this field is required.'.format(self.requirement)
            raise ValidationError({'event': msg})
        elif not self.requirement.event_required and self.event:
            msg = 'In the case of {}, this field must be left empty.'.format(self.requirement)
            raise ValidationError({'event': msg})

        super().clean()

    class Meta:
        ordering = ['created_at']


#------------------------------------------------------------


class Curriculum(ActiveMixin, models.Model):
    slug = models.CharField(
        max_length=STR_MED,
        null=False, blank=False, default="",
        unique=True,
        verbose_name="Curriculum ID",
        help_text="Use computer-friendly text here, e.g. 'dc-ecology-r'.",
    )
    name = models.CharField(
        max_length=200,
        null=False, blank=False, default="",
        unique=True,
        verbose_name="Curriculum name",
        help_text="Use user-friendly language, e.g. "
                  "'Data Carpentry (Ecology with R)'.",
    )
    unknown = models.BooleanField(
        null=False, blank=True, default=False,
        verbose_name="Unknown entry",
        help_text="Mark this curriculum record as 'I don't know yet', or "
                  "'Unknown', or 'Not sure yet'. There can be only one such "
                  "record in the database.",
    )

    class Meta:
        verbose_name = "Curriculum"
        verbose_name_plural = "Curricula"
        ordering = ["slug", ]

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
            Curriculum.objects.filter(unknown=True).update(unknown=False)
        return super().save(*args, **kwargs)


#------------------------------------------------------------


# This model should belong to extrequests app, but moving it is pain due to M2M
# relationship with WorkshopRequest.
class AcademicLevel(models.Model):
    name = models.CharField(max_length=STR_MED, null=False, blank=False)

    def __str__(self):
        return self.name


# This model should belong to extrequests app, but moving it is pain due to M2M
# relationship with WorkshopRequest.
class ComputingExperienceLevel(models.Model):
    # it's a long field because we need to store reasoning too, for example:
    # "Novice (uses a spreadsheet for data analysis rather than writing code)"
    name = models.CharField(max_length=STR_LONGEST, null=False, blank=False)

    def __str__(self):
        return self.name


@reversion.register
class WorkshopRequest(AssignmentMixin, StateMixin, CreatedUpdatedMixin,
                      DataPrivacyAgreementMixin, COCAgreementMixin,
                      HostResponsibilitiesMixin,
                      EventLink, models.Model):
    personal = models.CharField(
        max_length=STR_LONGEST,
        blank=False, null=False,
        verbose_name="Personal (given) name",
    )
    family = models.CharField(
        max_length=STR_LONGEST,
        blank=False, null=False,
        verbose_name="Family name (surname)",
    )
    email = models.EmailField(
        blank=False, null=False,
        verbose_name="Email address",
    )
    institution = models.ForeignKey(
        Organization, on_delete=models.PROTECT,
        blank=True, null=True,
        verbose_name="Institutional affiliation",
        help_text="If your institution isn't on the list, enter its name "
                  "in the field below.",
    )
    institution_name = models.CharField(
        max_length=STR_LONGEST,
        blank=True, null=False, default="",
        verbose_name="Name of institution you're affiliated with",
    )
    institution_department = models.CharField(
        max_length=STR_LONGEST,
        blank=True, null=False, default="",
        verbose_name="Department/school affiliation (if applicable)",
    )
    location = models.CharField(
        max_length=STR_LONGEST,
        blank=False, null=False, default="",
        verbose_name="Location",
        help_text="City, province/state.",
    )
    country = CountryField(
        null=False, blank=False,
        verbose_name="Country",
    )
    part_of_conference = models.BooleanField(
        null=False, blank=False,
        verbose_name="Is this workshop part of conference or larger event?",
        help_text="We can manage registration and other coordination for our"
                  " workshop, but not other conference activities.",
    )
    conference_details = models.CharField(
        max_length=STR_LONGEST,
        blank=True, null=False, default="",
        verbose_name="Conference details",
        help_text="Name, description (if applicable).",
    )
    preferred_dates = models.CharField(
        max_length=STR_LONGEST,
        blank=False, null=False, default="",
        verbose_name="Preferred dates or date range",
        help_text="Because we need to coordinate with instructors, a minimum"
                  " of 2-3 months lead time is required for workshop"
                  " planning.",
    )
    language = models.ForeignKey(
        Language, on_delete=models.PROTECT,
        blank=False, null=False,
        verbose_name="Language",
        help_text="Our workshops are offered primarily in English, with a few "
                  "of our lessons available in Spanish. While materials are "
                  "mainly in English, we know it can be valuable to have an "
                  "instructor who speaks the native language of the learners. "
                  "We will attempt to locate Instructors speaking a particular"
                  " language, but cannot guarantee the availability of "
                  "non-English speaking Instructors."
    )
    ATTENDEES_NUMBER_CHOICES = (
        ('10-40', '10-40 (one room, two instructors)'),
        ('40-80', '40-80 (two rooms, four instructors)'),
        ('80-120', '80-120 (three rooms, six instructors)'),
    )
    number_attendees = models.CharField(
        max_length=15,
        choices=ATTENDEES_NUMBER_CHOICES,
        blank=False, null=False, default='10-40',
        verbose_name="Number of attendees",
        help_text="This number doesn't need to be precise, but will help us "
                  "decide how many instructors your workshop will need. "
                  "Each workshop must have at least two instructors.",
    )
    domains = models.ManyToManyField(
        KnowledgeDomain,
        blank=False,
        verbose_name="Domains or topic of interest for target audience",
        help_text="The attendees' academic field(s) of study, if known.",
    )
    domains_other = models.CharField(
        max_length=STR_LONGEST,
        blank=True, default='',
        verbose_name="Other domains",
    )
    academic_levels = models.ManyToManyField(
        AcademicLevel,
        verbose_name="Attendees' academic level / career stage",
        help_text="If you know the academic level(s) of your attendees, "
                  "indicate them here.",
    )
    computing_levels = models.ManyToManyField(
        ComputingExperienceLevel,
        verbose_name="Attendees' level of computing experience",
        help_text="Indicate the attendees' level of computing experience, if "
                  "known. We will ask attendees to fill in a skills survey "
                  "before the workshop, so this answer can be an "
                  "approximation.",
    )
    audience_description = models.TextField(
        verbose_name="Please describe your anticipated audience, including "
                     "their experience, background, and goals",
    )

    SWC_LESSONS_LINK = (
        '<a href="https://software-carpentry.org/lessons/">'
        'Software Carpentry lessons page</a>'
    )
    DC_LESSONS_LINK = (
        '<a href="http://www.datacarpentry.org/lessons/">'
        'Data Carpentry lessons page</a>'
    )
    LC_LESSONS_LINK = (
        '<a href="https://librarycarpentry.org/lessons/">'
        'Library Carpentry lessons page</a>'
    )
    requested_workshop_types = models.ManyToManyField(
        Curriculum, limit_choices_to={'active': True},
        blank=False,
        verbose_name="Which Carpentry workshop are you requesting?",
        help_text="If your learners are new to programming and primarily "
                  "interested in working with data, Data Carpentry is likely "
                  "the best choice. If your learners are interested in "
                  "learning more about programming, including version control"
                  " and automation, Software Carpentry is likely the best "
                  "match. If your learners are people working in library and "
                  "information related roles interested in learning data and "
                  "software skills, Library Carpentry is the best choice. "
                  "Please visit the " + SWC_LESSONS_LINK + ", "
                  + DC_LESSONS_LINK + ", or the " + LC_LESSONS_LINK +
                  " for more information about any of our lessons. If you’re "
                  "not sure and would like to discuss with us, please select "
                  "the 'Not sure' option above.",
    )

    ORGANIZATION_TYPE_CHOICES = (
        ("self", "Self-organized"),
        ("central", "Centrally-organized"),
    )
    SELF_ORGANIZED_NOTES = (
        "If you are already connected with The Carpentries certified "
        "Instructors, we welcome you to organize and run your own workshop "
        "without administrative assistance from our staff. In the case of "
        "self-organized workshops, you will work with your certified "
        "Instructors on all aspects of workshop organization, including "
        "curriculum and lesson planning, as well as logistical details such "
        "as learner registration. In order to use our name and logo at your "
        "event, we require that you follow our curriculum (described on the "
        "lessons pages above), have at least one certified Carpentries "
        "Instructor teaching at your event, and share workshop attendance "
        "data. There is no fee (mandated or suggested) for running a "
        "self-organized workshop."
    )
    CENTRALLY_ORGANIZED_NOTES = (
        "The Carpentries staff will work with you to recruit Instructors and "
        "support all other logistical details. Fees due to The Carpentries "
        "are described below."
    )
    organization_type = models.CharField(
        max_length=15,
        choices=ORGANIZATION_TYPE_CHOICES,
        blank=False, null=False, default=None,
        verbose_name="Will this be a self-organized or "
                     "centrally-organized workshop?",
    )
    self_organized_github = models.URLField(
        max_length=STR_LONGEST,
        blank=True, null=False,
        verbose_name="Link to workshop GitHub page",
        help_text="Please provide URL."
    )
    FEE_CHOICES = (
        ("nonprofit", "I am with a government site, university, or other "
                      "nonprofit. I understand the workshop fee of US$2500, "
                      "and agree to follow through on The Carpentries "
                      "invoicing process."),
        ("forprofit", "I am with a corporate or for-profit site. I understand "
                      "The Carpentries staff will contact me about workshop "
                      "fees. I will follow through on The Carpentries "
                      "invoicing process for the agreed upon fee."),
        ("member", "I am with a Member Organisation so the workshop fee does "
                   "not apply (Instructor travel costs will still apply)."),
        ("waiver", "I am requesting a waiver of the workshop fee (Instructor "
                   "travel costs will still apply)."),
    )
    centrally_organized_fee = models.CharField(
        max_length=20,
        choices=FEE_CHOICES,
        blank=False, null=False, default="nonprofit",
        verbose_name="Which of the following applies to your payment for the "
                     "administrative fee?",
    )
    waiver_circumstances = models.TextField(
        blank=True,
        verbose_name="Please explain the circumstances for your waiver "
                     "request",
        help_text="Required only if you request a waiver."
    )
    travel_expences_agreement = models.BooleanField(
        null=False, blank=False, default=False,
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
    TRAVEL_EXPENCES_MANAGEMENT_CHOICES = (
        ("booked", "Hotel and airfare will be booked by site; ground travel "
                   "and meals/incidentals will be reimbursed within 60 days."),
        ("reimbursed", "All expenses will be booked by instructors and "
                       "reimbursed within 60 days."),
        ("", "Other:"),
    )
    travel_expences_management = models.CharField(
        max_length=20,
        null=False, blank=False,
        choices=TRAVEL_EXPENCES_MANAGEMENT_CHOICES,
        verbose_name="How will you manage travel expenses for Carpentries "
                     "Instructors?",
    )
    travel_expences_management_other = models.CharField(
        max_length=STR_LONGEST,
        null=False, blank=True, default='',
        verbose_name="Other travel expences management",
    )

    comment = models.TextField(
        blank=True,
        verbose_name="Is there anything else you would like to share with us?",
    )
    admin_comment = models.TextField(
        blank=True,
        verbose_name="Admin comment",
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return (
            'Workshop request ({institution}, {personal} {family}) - {state}'
        ).format(
            institution=str(self.institution or self.institution_name),
            personal=self.personal,
            family=self.family,
            state=self.get_state_display(),
        )

    def get_absolute_url(self):
        return reverse('workshoprequest_details', args=[self.id])
