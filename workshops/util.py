# coding: utf-8
import csv
import datetime
import re
from collections import namedtuple, defaultdict
from functools import wraps
from itertools import chain

import requests
import yaml
from django.contrib.auth.decorators import (
    user_passes_test,
    login_required as django_login_required
)
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import (
    EmptyPage,
    PageNotAnInteger,
    Paginator as DjangoPaginator,
)
from django.core.validators import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.http.response import HttpResponse
from django.http.response import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.utils.http import is_safe_url
from selectable.decorators import results_decorator

from workshops.models import (
    Event,
    Role,
    Person,
    Task,
    Badge,
    is_admin,
)

ITEMS_PER_PAGE = 25

WORD_SPLIT = re.compile(r'''([\s<>"']+)''')
SIMPLE_EMAIL = re.compile(r'^\S+@\S+\.\S+$')

NUM_TRIES = 100

ALLOWED_METADATA_NAMES = [
    'slug', 'startdate', 'enddate', 'country', 'venue', 'address',
    'latlng', 'language', 'eventbrite', 'instructor', 'helper', 'contact',
]


class InternalError(Exception):
    pass


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
        person_id = item.get('existing_person_id', None)
        person = None

        if person_id:
            try:
                person = Person.objects.get(id=int(person_id))
            except (ValueError, TypeError, Person.DoesNotExist):
                person = None
                info.append('Could not match selected person. New record will '
                            'be created.')
            else:
                info.append('Existing record for person will be used.')

        if not email and not person:
            info.append('It\'s highly recommended to add an email address.')

        if person:
            # force details from existing record
            item['personal'] = person.personal
            item['family'] = person.family
            item['email'] = person.email
            item['username'] = person.username
            item['person_exists'] = True
        else:
            # force a newly created username
            if not item.get('username'):
                item['username'] = create_username(personal, family)
            item['person_exists'] = False

            info.append('Person and task will be created.')

        # let's check if there's someone else named this way
        similar_persons = Person.objects.filter(
            Q(personal=personal, family=family) |
            Q(email=email) & ~Q(email='') & Q(email__isnull=False)
        )
        # need to cast to list, otherwise it won't JSON-ify
        item['similar_persons'] = list(similar_persons.values(
            'id', 'personal', 'middle', 'family', 'email', 'username',
        ))

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
                row_repr = ('{personal} {family} {username} <{email}>, '
                            '{role} at {event}').format(**row)

                fields = {key: row[key] for key in Person.PERSON_UPLOAD_FIELDS}
                fields['username'] = row['username']

                if row['person_exists'] and row['existing_person_id']:
                    # we should use existing Person
                    p = Person.objects.get(pk=row['existing_person_id'])

                elif row['person_exists'] and not row['existing_person_id']:
                    # we should use existing Person
                    p = Person.objects.get(
                        personal=fields['personal'], family=fields['family'],
                        username=fields['username'], email=fields['email'],
                    )

                else:
                    # we should create a new Person without any email provided
                    p = Person(**fields)
                    p.save()
                    persons_created.append(p)

                if row['event'] and row['role']:
                    e = Event.objects.get(slug=row['event'])
                    r = Role.objects.get(name=row['role'])

                    # if the number of learners attending the event changed,
                    # we should update ``event.attendance``
                    if row['role'] == 'learner':
                        events.add(e)

                    t, created = Task.objects.get_or_create(person=p, event=e,
                                                            role=r)
                    if created:
                        tasks_created.append(t)

            except IntegrityError as e:
                raise IntegrityError('{0} (for "{1}")'.format(str(e),
                                                              row_repr))

            except ObjectDoesNotExist as e:
                raise ObjectDoesNotExist('{0} (for "{1}")'.format(str(e),
                                                                  row_repr))

    for event in events:
        # if event.attendance is lower than number of learners, then
        # update the attendance
        update_event_attendance_from_tasks(event)

    return persons_created, tasks_created


def create_username(personal, family, tries=NUM_TRIES):
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

    # remove all non-alphanumeric, non-hyphen chars
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
        length = self._num_pages

        L = items[0:5]

        if index - 3 == 5:
            # Fix when two sets, L_s and M_s, are disjoint but make a sequence
            # [... 3 4, 5 6 ...], then there should not be dots between them
            M = items[index-4:index+4] or items[0:index+1]
        else:
            M = items[index-3:index+4] or items[0:index+1]

        if index + 4 == length - 5:
            # Fix when two sets, M_s and R_s, are disjoint but make a sequence
            # [... 3 4, 5 6 ...], then there should not be dots between them
            R = items[-6:]
        else:
            R = items[-5:]

        L_s = set(L)
        M_s = set(M)
        R_s = set(R)

        dots = [None]

        D1 = L_s.isdisjoint(M_s)
        D2 = M_s.isdisjoint(R_s)
        D3 = L_s.isdisjoint(R_s)

        if D1 and D2 and D3:
            # L…M…R
            pagination = chain(L, dots, M, dots, R)
        elif not D1 and D2 and D3:
            # LM…R
            pagination = chain(sorted(L_s | M_s), dots, R)
        elif D1 and not D2 and D3:
            # L…MR
            pagination = chain(L, dots, sorted(M_s | R_s))
        elif not D3:
            # tough situation, we may have split something wrong,
            # so lets just display all pages
            pagination = items
        else:
            # LMR
            pagination = iter(sorted(L_s | M_s | R_s))

        return pagination


def get_pagination_items(request, all_objects):
    '''Select paginated items.'''

    # Get parameters.
    items = request.GET.get('items_per_page', ITEMS_PER_PAGE)
    if items != 'all':
        try:
            items = int(items)
        except ValueError:
            items = ITEMS_PER_PAGE
    else:
        # Show everything.
        items = all_objects.count()

    # Figure out where we are.
    page = request.GET.get('page')

    # Show selected items.
    paginator = Paginator(all_objects, items)

    # Select the pages.
    try:
        result = paginator.page(page)

    # If page is not an integer, deliver first page.
    except PageNotAnInteger:
        result = paginator.page(1)

    # If page is out of range, deliver last page of results.
    except EmptyPage:
        result = paginator.page(paginator.num_pages)

    return result


def fetch_event_metadata(event_url):
    """Handle metadata from any event site (works with rendered <meta> metadata and
    YAML metadata in `index.html`)."""
    # fetch page
    response = requests.get(event_url)
    response.raise_for_status()  # assert it's 200 OK
    content = response.text

    # find metadata
    metadata = find_metadata_on_event_website(content)

    if 'slug' not in metadata:
        # there are no HTML metadata, so let's try the old method
        index_url, repository = generate_url_to_event_index(event_url)

        # fetch page
        response = requests.get(index_url)

        if response.status_code == 200:
            # don't throw errors for pages we fall back to
            content = response.text
            metadata = find_metadata_on_event_homepage(content)

            # add 'slug' metadata if missing
            if 'slug' not in metadata:
                metadata['slug'] = repository

    # leave normalization or validation to the caller function
    return metadata


class WrongWorkshopURL(ValueError):
    """Raised when we fall back to reading metadata from event's YAML front matter,
    which requires a link to GitHub raw hosted file, but we can't get that link
    because provided URL doesn't match Event.WEBSITE_REGEX
    (see `generate_url_to_event_index` below)."""

    def __str__(self):
        return 'Event\'s URL doesn\'t match Github website or repo format.'


def generate_url_to_event_index(website_url):
    """Given URL to workshop's website, generate a URL to its raw `index.html`
    file in GitHub repository."""
    template = ('https://raw.githubusercontent.com/{name}/{repo}'
                '/gh-pages/index.html')

    for regex in [Event.WEBSITE_REGEX, Event.REPO_REGEX]:
        results = regex.match(website_url)
        if results:
            return template.format(**results.groupdict()), results.group('repo')
    raise WrongWorkshopURL()


def find_metadata_on_event_homepage(content):
    """Given workshop's raw `index.html`, find and take YAML metadata that
    have workshop-related data."""
    try:
        first, header, last = content.split('---')
        metadata = yaml.load(header.strip())

        # get metadata to the form returned by `find_metadata_on_event_website`
        # because YAML tries to interpret values from index's header
        filtered_metadata = {key: value for key, value in metadata.items()
                         if key in ALLOWED_METADATA_NAMES}
        for key, value in filtered_metadata.items():
            if isinstance(value, int):
                filtered_metadata[key] = str(value)
            elif isinstance(value, datetime.date):
                filtered_metadata[key] = '{:%Y-%m-%d}'.format(value)
            elif isinstance(value, list):
                filtered_metadata[key] = ', '.join(value)

        return filtered_metadata

    except (ValueError, yaml.scanner.ScannerError):
        # can't unpack or header is not YML format
        return dict()


def find_metadata_on_event_website(content):
    """Given website content, find and take <meta> metadata that have
    workshop-related data."""

    R = r'<meta name="(?P<name>[\w-]+)" content="(?P<content>.+)" />$'
    regexp = re.compile(R, re.M)

    return {name: content for name, content in regexp.findall(content)
            if name in ALLOWED_METADATA_NAMES}


def parse_metadata_from_event_website(metadata):
    """Simple preprocessing of the metadata from event website."""
    # no compatibility with old-style names
    country = metadata.get('country', '').upper()[0:2]
    if len(country) < 2:
        country = ''
    language = metadata.get('language', '').upper()[0:2]
    if len(language) < 2:
        language = ''

    try:
        latitude, _ = metadata.get('latlng', '').split(',')
        latitude = float(latitude.strip())
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        latitude = None
    try:
        _, longitude = metadata.get('latlng', '').split(',')
        longitude = float(longitude.strip())
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        longitude = None

    try:
        reg_key = metadata.get('eventbrite', '')
        reg_key = int(reg_key)
    except (ValueError, TypeError):
        # value error: can't convert string to int
        # type error: can't convert None to int
        reg_key = None

    try:
        start = metadata.get('startdate', '')
        start = datetime.datetime.strptime(start, '%Y-%m-%d').date()
    except ValueError:
        start = None

    try:
        end = metadata.get('enddate', '')
        end = datetime.datetime.strptime(end, '%Y-%m-%d').date()
    except ValueError:
        end = None

    # Split string of comma-separated names into a list, but return empty list
    # instead of [''] when there are no instructors/helpers.
    instructors = (metadata.get('instructor') or '').split('|')
    instructors = [instr.strip() for instr in instructors if instr]
    helpers = (metadata.get('helper') or '').split('|')
    helpers = [helper.strip() for helper in helpers if helper]

    return {
        'slug': metadata.get('slug', ''),
        'language': language,
        'start': start,
        'end': end,
        'country': country,
        'venue': metadata.get('venue', ''),
        'address': metadata.get('address', ''),
        'latitude': latitude,
        'longitude': longitude,
        'reg_key': reg_key,
        'instructors': instructors,
        'helpers': helpers,
        'contact': metadata.get('contact', ''),
    }


def validate_metadata_from_event_website(metadata):
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
        required_ = requirement.required
        type_ = 'required' if required_ else 'optional'
        value_ = metadata.get(requirement.name)

        if value_ is None:
            errors.append('Missing {} metadata {}.'.format(type_, name_))

        if value_ == 'FIXME':
            errors.append('Placeholder value "FIXME" for {} metadata {}.'
                          .format(type_, name_))
        else:
            try:
                if required_ or value_:
                    if not re.match(requirement.match_format, value_):
                        errors.append(
                            'Invalid value "{}" for {} metadata {}: should be'
                            ' in format "{}".'
                            .format(value_, type_, name_,
                                    requirement.match_format)
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


def failed_to_delete(request, object, protected_objects, back=None):
    context = {
        'title': 'Failed to delete',
        'back': back or object.get_absolute_url,
        'object': object,
        'refs': defaultdict(list),
    }

    for obj in protected_objects:
        # e.g. for model Award its plural name is 'awards'
        name = str(obj.__class__._meta.verbose_name_plural)
        context['refs'][name].append(obj)

    # this trick enables looping through defaultdict instance
    context['refs'].default_factory = None

    return render(request, 'workshops/failed_to_delete.html', context)


def assign(request, obj, person_id):
    """Set obj.assigned_to. This view helper works with both POST and GET
    requests:

    * POST: read person ID from POST's person_1
    * GET: read person_id from URL
    * both: if person_id is None then make event.assigned_to empty
    * otherwise assign matching person.

    This is not a view, but it's used in some."""
    try:
        if request.method == "POST":
            person_id = request.POST.get('person_1', None)

        if person_id is None:
            obj.assigned_to = None
        else:
            person = Person.objects.get(pk=person_id)
            obj.assigned_to = person

        obj.save()

    except (Person.DoesNotExist, ValueError):
        raise Http404("No person found matching the query.")


def merge_objects(object_a, object_b, easy_fields, difficult_fields,
                  choices, base_a=True):
    """Merge two objects of the same model.

    `object_a` and `object_b` are two objects being merged. If `base_a==True`
    (default value), then object_b will be removed and object_a will stay
    after the merge.  If `base_a!=True` then object_a will be removed, and
    object_b will stay after the merge.

    `easy_fields` contains names of non-M2M-relation fields, while
    `difficult_fields` contains names of M2M-relation fields.

    Finally, `choices` is a dictionary of field name as a key and one of
    3 values: 'obj_a', 'obj_b', or 'combine'.

    This view can throw ProtectedError when removing an object is not allowed;
    in that case, this function's call should be wrapped in try-except
    block."""
    if base_a:
        base_obj = object_a
        merging_obj = object_b
    else:
        base_obj = object_b
        merging_obj = object_a

    # used to catch all IntegrityErrors caused by violated database constraints
    # when adding two similar entries by the manager (see below for more
    # details)
    integrity_errors = []

    with transaction.atomic():
        for attr in easy_fields:
            value = choices.get(attr)
            if value == 'obj_a':
                setattr(base_obj, attr, getattr(object_a, attr))
            elif value == 'obj_b':
                setattr(base_obj, attr, getattr(object_b, attr))
            elif value == 'combine':
                try:
                    new_value = (getattr(object_a, attr) +
                                 getattr(object_b, attr))
                    setattr(base_obj, attr, new_value)
                except TypeError:
                    # probably 'unsupported operand type', but we
                    # can't do much about it…
                    pass

        for attr in difficult_fields:
            related_a = getattr(object_a, attr)
            related_b = getattr(object_b, attr)

            manager = getattr(base_obj, attr)
            value = choices.get(attr)

            # switch only if this is opposite object
            if value == 'obj_a' and manager != related_a:
                if hasattr(manager, 'clear'):
                    # M2M and FK with `null=True` have `.clear()` method
                    # which unassigns instead of removing the related objects
                    manager.clear()
                else:
                    # in some cases FK are strictly related with the instance
                    # ie. they cannot be unassigned (`null=False`), so the
                    # only sensible solution is to remove them
                    manager.all().delete()
                manager.set(list(related_a.all()))

            elif value == 'obj_b' and manager != related_b:
                if hasattr(manager, 'clear'):
                    # M2M and FK with `null=True` have `.clear()` method
                    # which unassigns instead of removing the related objects
                    manager.clear()
                else:
                    # in some cases FK are strictly related with the instance
                    # ie. they cannot be unassigned (`null=False`), so the
                    # only sensible solution is to remove them
                    manager.all().delete()
                manager.set(list(related_b.all()))

            elif value == 'combine':
                summed = related_a.all() | related_b.all()

                # some entries may cause IntegrityError (violation of
                # uniqueness constraint) because they are duplicates *after*
                # being added by the manager
                for element in summed:
                    try:
                        with transaction.atomic():
                            manager.add(element)
                    except IntegrityError as e:
                        integrity_errors.append(str(e))

        merging_obj.delete()

        return base_obj.save(), integrity_errors


def access_control_decorator(decorator):
    """Every function-based view should be decorated with one of access control
    decorators, even if the view is accessible to everyone, including
    unauthorized users (in that case, use @login_not_required)."""
    @wraps(decorator)
    def decorated_access_control_decorator(view):
        acl = getattr(view, '_access_control_list', [])
        view = decorator(view)
        view._access_control_list = acl + [decorated_access_control_decorator]
        return view
    return decorated_access_control_decorator


@access_control_decorator
def admin_required(view):
    return user_passes_test(is_admin)(view)


@access_control_decorator
def login_required(view):
    return django_login_required(view)


@access_control_decorator
def login_not_required(view):
    # @access_control_decorator adds _access_control_list to `view`,
    # so @login_not_required is *not* no-op.
    return view


@results_decorator
def lookup_only_for_admins(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated():
        return HttpResponse(status=401)  # Unauthorized
    elif not is_admin(user):
        return HttpResponseForbidden()
    else:
        return None


class OnlyForAdminsMixin(UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)


class LoginNotRequiredMixin(object):
    pass



def redirect_with_next_support(request, *args, **kwargs):
    """Works in the same way as `redirect` except when there is GET parameter
    named "next". In that case, user is redirected to the URL from that
    parameter. If you have a class-based view, use RedirectSupportMixin that
    does the same. """

    next_url = request.GET.get('next', None)
    if next_url is not None and is_safe_url(next_url):
        return redirect(next_url)
    else:
        return redirect(*args, **kwargs)


def dict_without_Nones(**keys):
    return {k: v for k, v in keys.items() if v is not None}
