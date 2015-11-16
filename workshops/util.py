# coding: utf-8
import csv
from math import pi, sin, cos, acos
import re

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.paginator import Paginator as DjangoPaginator
from django_countries import countries
import requests

from workshops.check import get_header
from workshops.models import Event, Role, Person, Task, Award


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
                errors.append(u'Event with slug {0} does not exist.'
                              .format(event))

        role = item.get('role', None)
        existing_role = None
        if role:
            try:
                existing_role = Role.objects.get(name=role)
            except Role.DoesNotExist:
                errors.append(u'Role with name {0} does not exist.'
                              .format(role))
            except Role.MultipleObjectsReturned:
                errors.append(u'More than one role named {0} exists.'
                              .format(role))

        # check if the user exists, and if so: check if existing user's
        # personal and family names are the same as uploaded
        email = item.get('email', None)
        personal = item.get('personal', None)
        middle = item.get('middle', None)
        family = item.get('family', None)
        person = None
        if email:
            # we don't have to check if the user exists in the database
            # but we should check if, in case the email matches, family and
            # personal names match, too

            try:
                person = Person.objects.get(email__iexact=email)
                for (which, actual, uploaded) in (
                    ('personal', person.personal, personal),
                    ('middle', person.middle, middle),
                    ('family', person.family, family)):
                    if (actual == uploaded) or ((actual is None) and (uploaded == '')):
                        pass
                    else:
                        errors.append('{0}: database "{1}" vs uploaded "{2}"'
                                      .format(which, actual, uploaded))

            except Person.DoesNotExist:
                # in this case we need to add the user
                info.append('Person and task will be created.')

            else:
                if existing_event and person and existing_role:
                    # person, their role and a corresponding event exist, so
                    # let's check if the task exists
                    try:
                        Task.objects.get(event=existing_event, person=person,
                                         role=existing_role)
                    except Task.DoesNotExist:
                        info.append('Task will be created')
                    else:
                        info.append('Task already exists')

        if person:
            if not any([event, role]):
                errors.append("User exists but no event and role to assign to"
                              " the user to was provided")

        if (event and not role) or (role and not event):
            errors.append("Must have both: event ({0}) and role ({1})"
                          .format(event, role))

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
                fields['username'] = create_username(row['personal'],
                                                     row['family'])
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


def create_username(personal, family):
    '''Generate unique username.'''
    stem = normalize_name(family) + '.' + normalize_name(personal)
    counter = None
    while True:
        try:
            if counter is None:
                username = stem
                counter = 1
            else:
                counter += 1
                username = '{0}.{1}'.format(stem, counter)
            Person.objects.get(username=username)
        except ObjectDoesNotExist:
            break

    if any([ord(c) >= 128 for c in username]):
        raise InternalError('Normalized username still contains non-normal '
                            'characters "{0}"'.format(username))

    return username


def normalize_name(name):
    '''Get rid of spaces, funky characters, etc.'''
    name = name.strip()
    for (accented, flat) in [(' ', '-')]:
        name = name.replace(accented, flat)

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


class WrongEventURL(Exception):
    pass


def normalize_event_index_url(url):
    """From any event URL, make one URL to the raw content.

    For example:

    * http://user.github.io/SLUG/
    * http://user.github.io/SLUG/index.html
    * https://github.com/user/SLUG/
    * https://github.com/user/SLUG/blob/gh-pages/index.html
    * https://raw.githubusercontent.com/user/SLUG/gh-pages/index.html

    …will become:
    https://raw.githubusercontent.com/user/SLUG/gh-pages/index.html
    """
    template = ('https://raw.githubusercontent.com/{name}/{repo}'
                '/gh-pages/index.html')
    formats = [
        r'https?://(?P<name>[^\.]+)\.github\.(io|com)/(?P<repo>[^/]+)/?',
        (r'https?://(?P<name>[^\.]+)\.github\.(io|com)/(?P<repo>[^/]+)/'
         r'index\.html'),
        r'https://github\.com/(?P<name>[^/]+)/(?P<repo>[^/]+)/?',
        (r'https://github\.com/(?P<name>[^/]+)/(?P<repo>[^/]+)/'
         r'blob/gh-pages/index\.html'),
        (r'https://raw.githubusercontent.com/(?P<name>[^/]+)/(?P<repo>[^/]+)'
         r'/gh-pages/index.html'),
    ]
    for format in formats:
        results = re.match(format, url)
        if results:
            repo = results.groupdict()['repo']
            return template.format(**results.groupdict()), repo

    raise WrongEventURL("This event URL is incorrect: {0}".format(url))


def parse_tags_from_event_index(orig_url):
    url, slug = normalize_event_index_url(orig_url)
    response = requests.get(url)

    # will throw requests.exceptions.HTTPError if status is not OK
    response.raise_for_status()

    _, headers = get_header(response.text)

    try:
        latitude, longitude = headers.get('latlng', '').split(',')
        latitude = latitude.strip()
        longitude = longitude.strip()
    except ValueError:
        latitude, longitude = '', ''

    country = headers.get('country', '')
    if len(country) == 2:
        # special case: we're asking workshops to have country as a 2-letter
        # code, but for now most of them use (semi-)full country names
        country = country.upper()
    elif len(country):
        # probably a full-length country name
        countries_codes = {name: code for code, name in countries}
        country = country.replace('-', ' ')
        country = countries_codes.get(country, country)

    # put instructors, helpers and venue into notes
    notes = """INSTRUCTORS: {instructors}

HELPERS: {helpers}

COUNTRY: {country}""".format(
        country=country,
        instructors=", ".join(headers.get('instructor') or []),
        helpers=", ".join(headers.get('helper') or []),
    )

    return {
        'slug': slug,
        'start': headers.get('startdate', ''),
        'end': headers.get('enddate', ''),
        # A neat trick to get website URL easily.  It creates an Event object
        # (but doesn't add it to the database) and uses it's translating
        # @property 'website_url's
        'url': Event(url=orig_url).website_url,
        'reg_key': headers.get('eventbrite', ''),
        'contact': headers.get('contact', ''),
        'notes': notes,
        'venue': headers.get('venue', ''),
        'address': headers.get('address', ''),
        'country': country,
        'latitude': latitude,
        'longitude': longitude,
    }


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
