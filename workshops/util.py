# coding: utf-8
from collections import namedtuple
import csv
import datetime
from math import pi, sin, cos, acos
import re
import yaml

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.paginator import Paginator as DjangoPaginator

from workshops.models import Event, Role, Person, Task, Award, Badge

WORD_SPLIT = re.compile(r'''([\s<>"']+)''')
SIMPLE_EMAIL = re.compile(r'^\S+@\S+\.\S+$')


class InternalError(Exception):
    pass


def earth_distance(pos1, pos2):
    '''Taken from http://www.johndcook.com/python_longitude_latitude.html.'''

    # Extract fields.
    lat1, long1 = pos1
    lat2, long2 = pos2

    # Convert latitude and longitude to spherical coordinates in radians.
    degrees_to_radians = pi/180.0

    # phi = 90 - latitude
    phi1 = (90.0 - lat1) * degrees_to_radians
    phi2 = (90.0 - lat2) * degrees_to_radians

    # theta = longitude
    theta1 = long1 * degrees_to_radians
    theta2 = long2 * degrees_to_radians

    # Compute spherical distance from spherical coordinates.
    # For two locations in spherical coordinates
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    c = sin(phi1) * sin(phi2) * cos(theta1 - theta2) + cos(phi1) * cos(phi2)

    # due to round-off errors, sometimes c may be out of range
    if c > 1:
        c = 1
    if c < -1:
        c = -1
    arc = acos(c)

    # Multiply by 6373 to get distance in km.
    return arc * 6373


def upload_person_task_csv(stream):
    """Read people from CSV and return a JSON-serializable list of dicts.

    The input `stream` should be a file-like object that returns
    Unicode data.

    "Serializability" is required because we put this data into session.  See
    https://docs.djangoproject.com/en/1.7/topics/http/sessions/ for details.

    Also return a list of fields from Person.PERSON_UPLOAD_FIELDS for which
    no data was given.
    """

    result = []
    reader = csv.DictReader(stream)
    empty_fields = set()

    for row in reader:
        # skip empty lines in the CSV
        if not any(row.values()):
            continue

        entry = {}
        for col in Person.PERSON_UPLOAD_FIELDS:
            try:
                entry[col] = row[col].strip()
            except (KeyError, IndexError, AttributeError):
                # either `col` is not in `entry`, or not in `row`, or
                # `.strip()` doesn't work (e.g. `row[col]` gives `None` instead
                # of string)
                entry[col] = None
                empty_fields.add(col)

        for col in Person.PERSON_TASK_EXTRA_FIELDS:
            entry[col] = row.get(col, None)
        entry['errors'] = None

        # it will be set in the `verify_upload_person_task`
        entry['username'] = ''

        result.append(entry)

    return result, list(empty_fields)


def verify_upload_person_task(data):
    """
    Verify that uploaded data is correct.  Show errors by populating ``errors``
    dictionary item.  This function changes ``data`` in place.
    """

    errors_occur = False
    for item in data:
        errors = []
        info = []

        event = item.get('event', None)
        existing_event = None
        if event:
            try:
                existing_event = Event.objects.get(slug=event)
            except Event.DoesNotExist:
                errors.append('Event with slug {0} does not exist.'
                              .format(event))

        role = item.get('role', None)
        existing_role = None
        if role:
            try:
                existing_role = Role.objects.get(name=role)
            except Role.DoesNotExist:
                errors.append('Role with name {0} does not exist.'
                              .format(role))
            except Role.MultipleObjectsReturned:
                errors.append('More than one role named {0} exists.'
                              .format(role))

        # check if the user exists, and if so: check if existing user's
        # personal and family names are the same as uploaded
        email = item.get('email', None)
        personal = item.get('personal', None)
        family = item.get('family', None)
        person = None

        if email:
            try:
                # check if first and last name matches person in the database
                person = Person.objects.get(email__iexact=email)

                for which, actual, uploaded in (
                        ('personal', person.personal, personal),
                        ('family', person.family, family)
                ):
                    if (actual == uploaded) or (not actual and not uploaded):
                        pass
                    else:
                        errors.append('{0} mismatch: database "{1}" '
                                      'vs uploaded "{2}".'
                                      .format(which, actual, uploaded))

            except Person.DoesNotExist:
                # in this case we need to add a new person
                pass

            else:
                if existing_event and person and existing_role:
                    # person, their role and a corresponding event exist, so
                    # let's check if the task exists
                    try:
                        Task.objects.get(event=existing_event, person=person,
                                         role=existing_role)
                    except Task.DoesNotExist:
                        info.append('Task will be created.')
                    else:
                        info.append('Task already exists.')
        else:
            info.append('It\'s highly recommended to add an email address.')

        if person:
            # force username from existing record
            item['username'] = person.username
            item['person_exists'] = True

        else:
            # force a newly created username
            if not item.get('username'):
                item['username'] = create_username(personal, family)
            item['person_exists'] = False

            info.append('Person and task will be created.')

            try:
                # let's check if there's someone else named this way
                similar_person = Person.objects.get(personal=personal,
                                                    family=family)

            except Person.DoesNotExist:
                pass

            except Person.MultipleObjectsReturned:
                persons = [
                    str(person) for person in
                    Person.objects.filter(personal=personal, family=family)
                ]
                info.append('There\'s a couple of matching persons in the '
                            'database: {}. '
                            'Use email to merge.'.format(', '.join(persons)))

            else:
                info.append('There\'s a matching person in the database: {}. '
                            'Use their email to merge.'.format(similar_person))

        # let's check what Person model validators want to say
        try:
            p = Person(personal=personal, family=family, email=email,
                       username=item['username'])
            p.clean_fields(exclude=['password'])
        except ValidationError as e:
            for k, v in e.message_dict.items():
                errors.append('{}: {}'.format(k, v))

        if not role:
            errors.append('Must have a role.')

        if not event:
            errors.append('Must have an event.')

        if errors:
            errors_occur = True
            item['errors'] = errors

        if info:
            item['info'] = info

    return errors_occur


def create_uploaded_persons_tasks(data):
    """
    Create persons and tasks from upload data.
    """

    # Quick sanity check.
    if any([row.get('errors') for row in data]):
        raise InternalError('Uploaded data contains errors, cancelling upload')

    persons_created = []
    tasks_created = []
    events = set()

    with transaction.atomic():
        for row in data:
            try:
                fields = {key: row[key] for key in Person.PERSON_UPLOAD_FIELDS}
                fields['username'] = row['username']

                if fields['email']:
                    # we should use existing Person or create one
                    p, created = Person.objects.get_or_create(
                        email__iexact=fields['email'], defaults=fields
                    )

                    if created:
                        persons_created.append(p)

                else:
                    # we should create a new Person without any email provided
                    p = Person(**fields)
                    p.save()
                    persons_created.append(p)

                if row['event'] and row['role']:
                    e = Event.objects.get(slug=row['event'])
                    r = Role.objects.get(name=row['role'])

                    # is the number of learners attending the event changed,
                    # we should update ``event.attendance``
                    if row['role'] == 'learner':
                        events.add(e)

                    t, created = Task.objects.get_or_create(person=p, event=e,
                                                            role=r)
                    if created:
                        tasks_created.append(t)

            except IntegrityError as e:
                raise IntegrityError('{0} (for {1})'.format(str(e), row))

            except ObjectDoesNotExist as e:
                raise ObjectDoesNotExist('{0} (for {1})'.format(str(e), row))

    for event in events:
        # if event.attendance is lower than number of learners, then
        # update the attendance
        update_event_attendance_from_tasks(event)

    return persons_created, tasks_created


def create_username(personal, family, tries=100):
    '''Generate unique username.'''
    stem = normalize_name(family) + '_' + normalize_name(personal)

    counter = None
    for i in range(tries):  # let's limit ourselves to only 100 tries
        try:
            if counter is None:
                username = stem
                counter = 1
            else:
                counter += 1
                username = '{0}_{1}'.format(stem, counter)
            Person.objects.get(username=username)
        except ObjectDoesNotExist:
            return username

    raise InternalError('Cannot find a non-repeating username'
                        '(tried {} usernames): {}.'.format(tries, username))


def normalize_name(name):
    '''Get rid of spaces, funky characters, etc.'''
    name = name.strip()
    for (accented, flat) in [(' ', '-')]:
        name = name.replace(accented, flat)

    # remove all non-ASCII, non-hyphen chars
    name = re.sub(r'[^\w\-]', '', name, flags=re.A)

    # We should use lower-cased username, because it directly corresponds to
    # some files Software Carpentry stores about some people - and, as we know,
    # some filesystems are not case-sensitive.
    return name.lower()


class Paginator(DjangoPaginator):
    """Everything should work as in django.core.paginator.Paginator, except
    this class provides additional generator for nicer set of pages."""

    _page_number = None

    def page(self, number):
        """Overridden to store retrieved page number somewhere."""
        self._page_number = number
        return super().page(number)

    def paginate_sections(self):
        """Divide pagination range into 3 sections.

        Each section should contain approx. 5 links.  If sections are
        overlapping, they're merged.
        The results might be:
        * L…M…R
        * LM…R
        * L…MR
        * LMR
        where L - left section, M - middle section, R - right section, and "…"
        stands for a separator.
        """
        index = int(self._page_number) or 1
        items = self.page_range
        L = items[0:5]
        M = items[index-3:index+4] or items[0:index+1]
        R = items[-5:]
        L_s = set(L)
        M_s = set(M)
        R_s = set(R)

        D1 = L_s.isdisjoint(M_s)
        D2 = M_s.isdisjoint(R_s)

        if D1 and D2:
            # L…M…R
            pagination = L + [None] + M + [None] + R
        elif not D1 and D2:
            # LM…R
            pagination = sorted(L_s | M_s) + [None] + R
        elif D1 and not D2:
            # L…MR
            pagination = L + [None] + sorted(M_s | R_s)
        else:
            # LMR
            pagination = sorted(L_s | M_s | R_s)

        return pagination


def merge_persons(person_from, person_to):
    for award in person_from.award_set.all():
        try:
            award.person = person_to
            award.save()
        except IntegrityError:
            # unique constraints fail (probably)
            pass

    for task in person_from.task_set.all():
        try:
            task.person = person_to
            task.save()
        except IntegrityError:
            # unique constraints fail (probably)
            pass

    # update only unique lessons
    person_from.qualification_set.exclude(lesson__in=person_to.lessons.all()) \
                                 .update(person=person_to)

    person_to.domains.add(*person_from.domains.all())

    # removes tasks, awards, qualifications in a cascading way
    person_from.delete()


class WrongWorkshopURL(ValueError):
    """Raised when we fall back to reading tags from event's YAML front matter,
    which requires a link to GitHub raw hosted file, but we can't get that link
    because provided URL doesn't match Event.WEBSITE_REGEX
    (see `generate_url_to_event_index` below)."""

    def __str__(self):
        return ('Event\'s URL doesn\'t match Github website format '
                '"http://user.github.io/2015-12-08-workshop".')


def generate_url_to_event_index(website_url):
    """Given URL to workshop's website, generate a URL to its raw `index.html`
    file in GitHub repository."""
    template = ('https://raw.githubusercontent.com/{name}/{repo}'
                '/gh-pages/index.html')
    regex = Event.WEBSITE_REGEX

    results = regex.match(website_url)
    if results:
        return template.format(**results.groupdict()), results.group('repo')
    raise WrongWorkshopURL()

ALLOWED_TAG_NAMES = [
    'slug', 'startdate', 'enddate', 'country', 'venue', 'address',
    'latlng', 'language', 'eventbrite', 'instructor', 'helper', 'contact',
]


def find_tags_on_event_index(content):
    """Given workshop's raw `index.html`, find and take YAML tags that
    have workshop-related data."""
    try:
        first, header, last = content.split('---')
        tags = yaml.load(header.strip())

        # get tags to the form returned by `find_tags_on_event_website`
        # because YAML tries to interpret values from index's header
        filtered_tags = {key: value for key, value in tags.items()
                         if key in ALLOWED_TAG_NAMES}
        for key, value in filtered_tags.items():
            if isinstance(value, int):
                filtered_tags[key] = str(value)
            elif isinstance(value, datetime.date):
                filtered_tags[key] = '{:%Y-%m-%d}'.format(value)
            elif isinstance(value, list):
                filtered_tags[key] = ', '.join(value)

        return filtered_tags

    except (ValueError, yaml.scanner.ScannerError):
        # can't unpack or header is not YML format
        return dict()


def find_tags_on_event_website(content):
    """Given website content, find and take <meta> tags that have
    workshop-related data."""

    R = r'<meta name="(?P<name>[\w-]+)" content="(?P<content>.+)" />$'
    regexp = re.compile(R, re.M)

    return {name: content for name, content in regexp.findall(content)
            if name in ALLOWED_TAG_NAMES}


def parse_tags_from_event_website(tags):
    """Simple preprocessing of the tags from event website."""
    # no compatibility with old-style names
    country = tags.get('country', '').upper()[0:2]
    if len(country) < 2:
        country = ''
    language = tags.get('language', '').upper()[0:2]
    if len(language) < 2:
        language = ''

    try:
        latitude, _ = tags.get('latlng', '').split(',')
        latitude = float(latitude.strip())
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        latitude = None
    try:
        _, longitude = tags.get('latlng', '').split(',')
        longitude = float(longitude.strip())
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        longitude = None

    try:
        reg_key = tags.get('eventbrite', '')
        reg_key = int(reg_key)
    except (ValueError, TypeError):
        # value error: can't convert string to int
        # type error: can't convert None to int
        reg_key = None

    try:
        start = tags.get('startdate', '')
        start = datetime.datetime.strptime(start, '%Y-%m-%d').date()
    except ValueError:
        start = None

    try:
        end = tags.get('enddate', '')
        end = datetime.datetime.strptime(end, '%Y-%m-%d').date()
    except ValueError:
        end = None

    # Split string of comma-separated names into a list, but return empty list
    # instead of [''] when there are no instructors/helpers.
    instructors = tags.get('instructor', '').split('|')
    instructors = [instructor.strip() for instructor in instructors]
    instructors = [] if not any(instructors) else instructors
    helpers = tags.get('helper', '').split('|')
    helpers = [helper.strip() for helper in helpers]
    helpers = [] if not any(helpers) else helpers

    return {
        'slug': tags.get('slug', ''),
        'language': language,
        'start': start,
        'end': end,
        'country': country,
        'venue': tags.get('venue', ''),
        'address': tags.get('address', ''),
        'latitude': latitude,
        'longitude': longitude,
        'reg_key': reg_key,
        'instructors': instructors,
        'helpers': helpers,
        'contact': tags.get('contact', ''),
    }


def validate_tags_from_event_website(tags):
    errors = []

    Requirement = namedtuple(
        'Requirement',
        ['name', 'display', 'required', 'match_format'],
    )

    DATE_FMT = r'^\d{4}-\d{2}-\d{2}$'
    SLUG_FMT = r'^\d{4}-\d{2}-\d{2}-.+$'
    TWOCHAR_FMT = r'^\w\w$'
    FRACTION_FMT = r'[-+]?[0-9]*\.?[0-9]*'
    requirements = [
        Requirement('slug', 'workshop name', True, SLUG_FMT),
        Requirement('language', None, False, TWOCHAR_FMT),
        Requirement('startdate', 'start date', True, DATE_FMT),
        Requirement('enddate', 'end date', False, DATE_FMT),
        Requirement('country', None, True, TWOCHAR_FMT),
        Requirement('venue', None, True, None),
        Requirement('address', None, True, None),
        Requirement('latlng', 'latitude / longitude', True,
                    '^' + FRACTION_FMT + r',\s?' + FRACTION_FMT + '$'),
        Requirement('instructor', None, True, None),
        Requirement('helper', None, True, None),
        Requirement('contact', None, True, None),
        Requirement('eventbrite', 'Eventbrite event ID', False, r'^\d+$'),
    ]

    for requirement in requirements:
        d_ = requirement._asdict()
        name_ = ('{display} ({name})'.format(**d_)
                 if requirement.display
                 else '{name}'.format(**d_))
        type_ = 'required' if requirement.required else 'optional'
        value_ = tags.get(requirement.name)

        if not value_:
            errors.append('Missing {} tag {}.'.format(type_, name_))

        if value_ == 'FIXME':
            errors.append('Placeholder value "FIXME" for {} tag {}.'
                          .format(type_, name_))
        else:
            try:
                if not re.match(requirement.match_format, value_):
                    errors.append(
                        'Invalid value "{}" for {} tag {}: should be in '
                        'format "{}".'
                        .format(value_, type_, name_, requirement.match_format)
                    )
            except (re.error, TypeError):
                pass

    return errors


def update_event_attendance_from_tasks(event):
    """Increase event.attendance if there's more learner tasks belonging to the
    event."""
    learners = event.task_set.filter(role__name='learner').count()
    Event.objects \
        .filter(pk=event.pk) \
        .filter(Q(attendance__lt=learners) | Q(attendance__isnull=True)) \
        .update(attendance=learners)


def universal_date_format(date):
    return '{:%Y-%m-%d}'.format(date)


def get_members(earliest, latest):
    '''Get everyone who is a member of the Software Carpentry Foundation.'''

    member_badge = Badge.objects.get(name='member')
    instructor_badges = Badge.objects.instructor_badges()
    instructor_role = Role.objects.get(name='instructor')

    # Everyone who is an explicit member.
    explicit = Person.objects.filter(badges__in=[member_badge]).distinct()

    # Everyone who qualifies by having taught recently.
    implicit = Person.objects.filter(
        task__role=instructor_role,
        badges__in=instructor_badges,
        task__event__start__gte=earliest,
        task__event__start__lte=latest
    ).distinct()

    # Merge the two sets.
    return explicit | implicit


def default_membership_cutoff():
    "Calculate a default cutoff dates for members finding with `get_members`."
    earliest = datetime.date.today() - 2 * datetime.timedelta(days=365)
    latest = datetime.date.today()
    return earliest, latest


def find_emails(text):
    """Find emails in the text.  This is based on Django's own
    `django.utils.html.urlize`."""
    # Split into tokens in case someone uses for example
    # 'Name <name@gmail.com>' format.
    emails = []

    for word in WORD_SPLIT.split(text):
        if SIMPLE_EMAIL.match(word):
            local, domain = word.rsplit('@', 1)
            try:
                domain = domain.encode('idna').decode('ascii')
            except UnicodeError:
                continue
            emails.append('{}@{}'.format(local, domain))

    return emails


def assignment_selection(request):
    """Parse `assigned_to` query param depending on the logged-in user."""
    user = request.user
    is_admin = user.groups.filter(name='administrators').exists()

    # it's always possible to assign something entirely else
    # in the `?assigned_to` query param

    if is_admin:
        # One of the administrators.
        # They should be presented with their events by default.
        assigned_to = request.GET.get('assigned_to', 'me')

    elif user.is_superuser:
        # A superuser.  Should see all events by default
        assigned_to = request.GET.get('assigned_to', 'all')

    else:
        # Normal user (for example subcommittee members).
        assigned_to = 'all'

    return assigned_to, is_admin
