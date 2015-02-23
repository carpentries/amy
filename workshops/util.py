# coding: utf-8
from math import pi, sin, cos, acos
import csv

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction

from .models import Event, Role, Person, Task


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
        entry = {}
        for col in Person.PERSON_UPLOAD_FIELDS:
            if col in row:
                entry[col] = row[col].strip()
            else:
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

        event = item.get('event', None)
        if event:
            try:
                Event.objects.get(slug=event)
            except Event.DoesNotExist:
                errors.append(u'Event with slug {0} does not exist.'
                              .format(event))

        role = item.get('role', None)
        if role:
            try:
                Role.objects.get(name=role)
            except Role.DoesNotExist:
                errors.append(u'Role with name {0} does not exist.'
                              .format(role))
            except Role.MultipleObjectsReturned:
                errors.append(u'More than one role named {0} exists.'
                              .format(role))

        email = item.get('email', None)
        if email:
            try:
                Person.objects.get(email__iexact=email)
                errors.append('User with email {0} already exists.'
                              .format(email))
            except Person.DoesNotExist:
                # we want the email to be case-insensitive unique
                pass

        if (event and not role) or (role and not event):
            errors.append('Must have both or either of event ({0}) and role ({1})'
                          .format(event, role))

        if errors:
            errors_occur = True
            item['errors'] = errors

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
    with transaction.atomic():
        for row in data:
            try:
                fields = dict([(key, row[key]) for key in Person.PERSON_UPLOAD_FIELDS])
                fields['username'] = create_username(row['personal'], row['family'])
                p = Person(**fields)
                p.save()
                persons_created.append(p)

                if row['event'] and row['role']:
                    e = Event.objects.get(slug=row['event'])
                    r = Role.objects.get(name=row['role'])
                    t = Task(person=p, event=e, role=r)
                    t.save()
                    tasks_created.append(t)

            except IntegrityError as e:
                raise IntegrityError('{0} (for {1})'.format(str(e), row))

            except ObjectDoesNotExist as e:
                raise ObjectDoesNotExist('{0} (for {1})'.format(str(e), row))

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

    if any([ord(c) >=128 for c in username]):
        raise InternalError('Normalized username still contains non-normal characters "{0}"'
                            .format(username))

    return username


def normalize_name(name):
    '''Get rid of spaces, funky characters, etc.'''
    name = name.strip()
    for (accented, flat) in [(' ', '-')]:
        name = name.replace(accented, flat)
    return name
