# coding: utf-8
from math import pi, sin, cos, acos
from io import TextIOWrapper, StringIO
import csv

from django.conf import settings

from .models import Event, Role, Person


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


def upload_person_task_csv(uploaded_file, encoding=None):
    """
    Read data from CSV and turn it into JSON-serializable list of dictionaries.
    "Serializability" is required because we put this data into session.  See
    https://docs.djangoproject.com/en/1.7/topics/http/sessions/ for details.

    Also return a list of fields from Person.PERSON_UPLOAD_FIELDS for which
    no data was given.

    :param string encoding: encoding used to encode incoming file. Defaults to
                            ``django.conf.settings.DEFAULT_CHARSET``
    """
    persons_tasks = []

    if not encoding:
        encoding = settings.DEFAULT_CHARSET

    # we provide uploaded_file as StringIO in our tests (test_util.py)
    if not issubclass(StringIO, uploaded_file.__class__):
        # Django provides uploaded files as byte file objects.  We need to wrap
        # `uploaded_file` and provide it as a text file with specific encoding.
        # This way we force users to upload UTF-8 encoded files.
        uploaded_file = TextIOWrapper(uploaded_file.file, encoding=encoding)

    reader = csv.DictReader(uploaded_file)
    empty_fields = []
    for row in reader:
        person_fields = {}
        for col in Person.PERSON_UPLOAD_FIELDS:
            try:
                person_fields[col] = row[col].strip()
            except KeyError:
                if col not in empty_fields:
                    empty_fields.append(col)
        entry = {'person': person_fields, 'event': row.get('event', None),
                 'role': row.get('role', None), 'errors': None}
        persons_tasks.append(entry)
    return persons_tasks, empty_fields


def verify_upload_person_task(data):
    """
    Verify that uploaded data is correct.  Show errors by populating ``errors``
    dictionary item.

    This function changes ``data`` in place; ``data`` is a list, so it's
    passed by a reference.  This means any changes to ``data`` we make in
    here don't need to be returned via ``return`` statement.
    """

    errors_occur = False

    for item in data:
        errors = []
        event, role = item.get('event', None), item.get('role', None)
        try:
            email = item['person'].get('email', None)
        except KeyError:
            email = None
            errors.append("'person' key not in item")

        if event:
            try:
                Event.objects.get(slug=event)
            except Event.DoesNotExist:
                errors.append(u'Event with slug {} does not exist.'
                              .format(event))
        if role:
            try:
                Role.objects.get(name=role)
            except Role.DoesNotExist:
                errors.append(u'Role with name {} does not exist.'.format(role))
            except Role.MultipleObjectsReturned:
                errors.append(u'More than one role named {} exists.'
                              .format(role))

        if email:
            try:
                Person.objects.get(email__iexact=email)
                errors.append("User with email {} already exists."
                              .format(email))
            except Person.DoesNotExist:
                # we want the email to be case-insensitive unique
                pass

        if errors:
            # copy the errors just to be safe
            item['errors'] = errors[:]
            if not errors_occur:
                errors_occur = True

    # indicate there were some errors
    return errors_occur
