# coding: utf-8
from math import pi, sin, cos, acos
import csv

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import get_models, Model
from django.contrib.contenttypes.generic import GenericForeignKey

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

                assert person.personal == personal
                assert person.middle == middle
                assert person.family == family

            except Person.DoesNotExist:
                # in this case we need to add the user
                pass

            except AssertionError:
                errors.append(
                    "Personal, middle or family name of existing user don't"
                    " match: {0} vs {1}, {2} vs {3}, {4} vs {5}"
                    .format(personal, person.personal, middle, person.middle,
                            family, person.family)
                )

        if person:
            if not any([event, role]):
                errors.append("User exists but no event and role to assign"
                              " the user to was provided")

            else:
                # check for duplicate Task
                try:
                    Task.objects.get(event__slug=event, role__name=role,
                                     person=person)
                except Task.DoesNotExist:
                    pass
                else:
                    errors.append("Existing person {2} already has role {0}"
                                  " in event {1}".format(role, event, person))

        if (event and not role) or (role and not event):
            errors.append("Must have both or either of event ({0}) and role"
                          " ({1})".format(event, role))

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
                fields = {key: row[key] for key in Person.PERSON_UPLOAD_FIELDS}
                fields['username'] = create_username(row['personal'],
                                                     row['family'])
                if fields['email']:
                    # we should use existing Person or create one
                    p, created = Person.objects.get_or_create(
                        email=fields['email'], defaults=fields
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

# from https://djangosnippets.org/snippets/2283/
def merge_model_objects(primary_object, alias_objects=[], keep_old=False):
    """
    Use this function to merge model objects (i.e. Users, Organizations, Polls,
    etc.) and migrate all of the related fields from the alias objects to the
    primary object.
    
    Usage:
    from django.contrib.auth.models import User
    primary_user = User.objects.get(email='good_email@example.com')
    duplicate_user = User.objects.get(email='good_email+duplicate@example.com')
    merge_model_objects(primary_user, duplicate_user)
    """

    if isinstance(primary_object, list):
        raise TypeError('The primary object should not be a list')

    if not isinstance(alias_objects, list):
        alias_objects = [alias_objects]
    
    # check that all aliases are the same class as primary one and that
    # they are subclass of model
    primary_class = primary_object.__class__
    
    if not issubclass(primary_class, Model):
        raise TypeError('Only django.db.models.Model subclasses can be merged')
    
    for alias_object in alias_objects:
        if not isinstance(alias_object, primary_class):
            raise TypeError('Only models of same class can be merged')
    
    if primary_object in alias_objects:
        raise TypeError('The primary object should not be in alias_objects')

    # Get a list of all GenericForeignKeys in all models
    # TODO: this is a bit of a hack, since the generics framework should provide a similar
    # method to the ForeignKey field for accessing the generic related fields.
    generic_fields = []
    for model in get_models():
        for field_name, field in filter(lambda x: isinstance(x[1], GenericForeignKey), model.__dict__.items()):
            generic_fields.append(field)
            
    blank_local_fields = set([field.attname for field in primary_object._meta.local_fields if getattr(primary_object, field.attname) in [None, '']])
    
    # Loop through all alias objects and migrate their data to the primary object.
    for alias_object in alias_objects:
        # Migrate all foreign key references from alias object to primary object.
        for related_object in alias_object._meta.get_all_related_objects():
            # The variable name on the alias_object model.
            alias_varname = related_object.get_accessor_name()
            # The variable name on the related model.
            obj_varname = related_object.field.name
            related_objects = getattr(alias_object, alias_varname)
            for obj in related_objects.all():
                setattr(obj, obj_varname, primary_object)
                obj.save()

        # Migrate all many to many references from alias object to primary object.
        for related_many_object in alias_object._meta.get_all_related_many_to_many_objects():
            alias_varname = related_many_object.get_accessor_name()
            obj_varname = related_many_object.field.name
            
            if alias_varname is not None:
                # standard case
                related_many_objects = getattr(alias_object, alias_varname).all()
            else:
                # special case, symmetrical relation, no reverse accessor
                related_many_objects = getattr(alias_object, obj_varname).all()
            for obj in related_many_objects.all():
                getattr(obj, obj_varname).remove(alias_object)
                getattr(obj, obj_varname).add(primary_object)

        # Migrate all generic foreign key references from alias object to primary object.
        for field in generic_fields:
            filter_kwargs = {}
            filter_kwargs[field.fk_field] = alias_object._get_pk_val()
            filter_kwargs[field.ct_field] = field.get_content_type(alias_object)
            for generic_related_object in field.model.objects.filter(**filter_kwargs):
                setattr(generic_related_object, field.name, primary_object)
                generic_related_object.save()
                
        # Try to fill all missing values in primary object by values of duplicates
        filled_up = set()
        for field_name in blank_local_fields:
            val = getattr(alias_object, field_name) 
            if val not in [None, '']:
                setattr(primary_object, field_name, val)
                filled_up.add(field_name)
        blank_local_fields -= filled_up
            
        if not keep_old:
            alias_object.delete()
    primary_object.save()
    return primary_object
