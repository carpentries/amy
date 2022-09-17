from collections import defaultdict, namedtuple
import datetime
from hashlib import sha1
import re

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import IntegrityError, models, transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django_comments.models import Comment
import requests
import yaml

from consents.models import Consent
from dashboard.models import Criterium
from workshops.exceptions import WrongWorkshopURL
from workshops.models import STR_LONG, STR_MED, Badge, Event, Person, Role

WORD_SPLIT = re.compile(r"""([\s<>"']+)""")
SIMPLE_EMAIL = re.compile(r"^\S+@\S+\.\S+$")


ALLOWED_METADATA_NAMES = [
    "slug",
    "startdate",
    "enddate",
    "country",
    "venue",
    "address",
    "latlng",
    "lat",
    "lng",
    "language",
    "eventbrite",
    "instructor",
    "helper",
    "contact",
]


def fetch_workshop_metadata(event_url, timeout=5):
    """Handle metadata from any event site (works with rendered <meta> tags
    metadata or YAML metadata in `index.html`)."""
    # fetch page
    response = requests.get(event_url, timeout=timeout)
    response.raise_for_status()  # assert it's 200 OK
    content = response.text

    # find metadata
    metadata = find_workshop_HTML_metadata(content)

    if not metadata:
        # there are no HTML metadata, so let's try the old method
        index_url, repository = generate_url_to_event_index(event_url)

        # fetch page
        response = requests.get(index_url, timeout=timeout)

        if response.status_code == 200:
            # don't throw errors for pages we fall back to
            content = response.text
            metadata = find_workshop_YAML_metadata(content)

            # add 'slug' metadata if missing
            if "slug" not in metadata:
                metadata["slug"] = repository

    # leave normalization or validation to the caller function
    return metadata


def generate_url_to_event_index(website_url):
    """Given URL to workshop's website, generate a URL to its raw `index.html`
    file in GitHub repository."""
    template = "https://raw.githubusercontent.com/{name}/{repo}" "/gh-pages/index.html"

    for regex in [Event.WEBSITE_REGEX, Event.REPO_REGEX]:
        results = regex.match(website_url)
        if results:
            return template.format(**results.groupdict()), results.group("repo")
    raise WrongWorkshopURL("URL doesn't match Github website or repo format.")


def find_workshop_YAML_metadata(content):
    """Given workshop's raw `index.html`, find and take YAML metadata that
    have workshop-related data."""
    try:
        first, header, last = content.split("---")
        metadata = yaml.load(header.strip(), Loader=yaml.SafeLoader)

        # get metadata to the form returned by `find_workshop_HTML_metadata`
        # because YAML tries to interpret values from index's header
        filtered_metadata = {
            key: value
            for key, value in metadata.items()
            if key in ALLOWED_METADATA_NAMES
        }
        for key, value in filtered_metadata.items():
            if isinstance(value, int) or isinstance(value, float):
                filtered_metadata[key] = str(value)
            elif isinstance(value, datetime.date):
                filtered_metadata[key] = "{:%Y-%m-%d}".format(value)
            elif isinstance(value, list):
                filtered_metadata[key] = "|".join(value)

        return filtered_metadata

    except (ValueError, yaml.scanner.ScannerError):
        # can't unpack or header is not YML format
        return dict()


def find_workshop_HTML_metadata(content):
    """Given website content, find and take <meta> metadata that have
    workshop-related data."""

    R = r'<meta\s+name="(?P<name>\w+?)"\s+content="(?P<content>.*?)"\s*?/?>'
    regexp = re.compile(R)

    return {
        name: content
        for name, content in regexp.findall(content)
        if name in ALLOWED_METADATA_NAMES
    }


def parse_workshop_metadata(metadata):
    """Simple preprocessing of the metadata from event website."""
    # no compatibility with old-style names
    country = metadata.get("country", "").upper()[0:2]
    if len(country) < 2:
        country = ""
    language = metadata.get("language", "").upper()[0:2]
    if len(language) < 2:
        language = ""

    # read either ('lat', 'lng') pair or (old) 'latlng' comma-separated value
    if "lat" in metadata and "lng" in metadata:
        latitude = metadata.get("lat", "")
        longitude = metadata.get("lng", "")
    else:
        try:
            latitude, longitude = metadata.get("latlng", "").split(",")
        except (ValueError, AttributeError):
            latitude, longitude = None, None

    try:
        latitude = float(latitude.strip())
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        latitude = None
    try:
        longitude = float(longitude.strip())
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        longitude = None

    try:
        reg_key = metadata.get("eventbrite", "")
        reg_key = int(reg_key)
    except (ValueError, TypeError):
        # value error: can't convert string to int
        # type error: can't convert None to int
        reg_key = None

    try:
        start = metadata.get("startdate", "")
        start = datetime.datetime.strptime(start, "%Y-%m-%d").date()
    except ValueError:
        start = None

    try:
        end = metadata.get("enddate", "")
        end = datetime.datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        end = None

    # Split string of comma-separated names into a list, but return empty list
    # instead of [''] when there are no instructors/helpers/contacts.
    instructors = (metadata.get("instructor") or "").split("|")
    instructors = [instr.strip() for instr in instructors if instr]
    helpers = (metadata.get("helper") or "").split("|")
    helpers = [helper.strip() for helper in helpers if helper]
    contact = (metadata.get("contact") or "").split("|")
    contact = [c.strip() for c in contact if c]

    return {
        "slug": metadata.get("slug", ""),
        "language": language,
        "start": start,
        "end": end,
        "country": country,
        "venue": metadata.get("venue", ""),
        "address": metadata.get("address", ""),
        "latitude": latitude,
        "longitude": longitude,
        "reg_key": reg_key,
        "instructors": instructors,
        "helpers": helpers,
        "contact": contact,
    }


def validate_workshop_metadata(metadata):
    errors = []
    warnings = []

    Requirement = namedtuple(
        "Requirement",
        ["name", "display", "required", "match_format"],
    )

    DATE_FMT = r"^\d{4}-\d{2}-\d{2}$"
    SLUG_FMT = r"^\d{4}-\d{2}-\d{2}-.+$"
    TWOCHAR_FMT = r"^\w\w$"
    FRACTION_FMT = r"[-+]?[0-9]*\.?[0-9]*"
    requirements = [
        Requirement("slug", "workshop name", True, SLUG_FMT),
        Requirement("language", None, False, TWOCHAR_FMT),
        Requirement("startdate", "start date", True, DATE_FMT),
        Requirement("enddate", "end date", False, DATE_FMT),
        Requirement("country", None, True, TWOCHAR_FMT),
        Requirement("venue", None, True, None),
        Requirement("address", None, True, None),
        Requirement("instructor", None, True, None),
        Requirement("helper", None, True, None),
        Requirement("contact", None, True, None),
        Requirement("eventbrite", "Eventbrite event ID", False, r"^\d+$"),
    ]

    # additional, separate check for latitude and longitude data
    latlng_req = Requirement(
        "latlng",
        "latitude / longitude",
        True,
        r"^{},\s?{}$".format(FRACTION_FMT, FRACTION_FMT),
    )
    lat_req = Requirement("lat", "latitude", True, "^" + FRACTION_FMT + "$")
    lng_req = Requirement("lng", "longitude", True, "^" + FRACTION_FMT + "$")

    # separate 'lat' and 'lng' are supported since #1461,
    # but here we're checking which requirement to add to the list of
    # "required" requirements
    if "lat" in metadata or "lng" in metadata:
        requirements.append(lat_req)
        requirements.append(lng_req)
    else:
        requirements.append(latlng_req)

    for requirement in requirements:
        d_ = requirement._asdict()
        name_ = (
            "{display} ({name})".format(**d_)
            if requirement.display
            else "{name}".format(**d_)
        )
        required_ = requirement.required
        type_ = "required" if required_ else "optional"
        value_ = metadata.get(requirement.name)

        if value_ is None:
            issues = errors if required_ else warnings
            issues.append("Missing {} metadata {}.".format(type_, name_))

        if value_ == "FIXME":
            errors.append(
                'Placeholder value "FIXME" for {} metadata {}.'.format(type_, name_)
            )
        else:
            try:
                if required_ or value_:
                    if not re.match(requirement.match_format, value_):
                        errors.append(
                            'Invalid value "{}" for {} metadata {}: should be'
                            ' in format "{}".'.format(
                                value_, type_, name_, requirement.match_format
                            )
                        )
            except (re.error, TypeError):
                pass

    return errors, warnings


def get_members(earliest, latest):
    """Get everyone who is a member of the Software Carpentry Foundation."""

    member_badge = Badge.objects.get(name="member")
    instructor_badges = Badge.objects.instructor_badges()
    instructor_role = Role.objects.get(name="instructor")

    # Everyone who is an explicit member.
    explicit = Person.objects.filter(badges__in=[member_badge]).distinct()

    # Everyone who qualifies by having taught recently.
    implicit = Person.objects.filter(
        task__role=instructor_role,
        badges__in=instructor_badges,
        task__event__start__gte=earliest,
        task__event__start__lte=latest,
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
            local, domain = word.rsplit("@", 1)
            try:
                domain = domain.encode("idna").decode("ascii")
            except UnicodeError:
                continue
            emails.append("{}@{}".format(local, domain))

    return emails


def failed_to_delete(request, object, protected_objects, back=None):
    context = {
        "title": "Failed to delete",
        "back": back or object.get_absolute_url,
        "object": object,
        "refs": defaultdict(list),
    }

    for obj in protected_objects:
        # e.g. for model Award its plural name is 'awards'
        name = str(obj.__class__._meta.verbose_name_plural)
        context["refs"][name].append(obj)

    # this trick enables looping through defaultdict instance
    context["refs"].default_factory = None

    return render(request, "workshops/failed_to_delete.html", context)


def assign(request, obj, person_id):
    """Set obj.assigned_to. This view helper works with both POST and GET
    requests:

    * POST: read person ID from POST's `person`
    * GET: read person_id from URL
    * both: if person_id is None then make event.assigned_to empty
    * otherwise assign matching person.

    This is not a view, but it's used in some."""
    try:
        if request.method == "POST":
            person_id = request.POST.get("person", None)

        if person_id is None:
            obj.assigned_to = None
        else:
            person = Person.objects.get(pk=person_id)
            obj.assigned_to = person

        obj.save()

    except (Person.DoesNotExist, ValueError):
        raise Http404("No person found matching the query.")


def archive_least_recent_active_consents(object_a, object_b, base_obj):
    """
    There is a unique database constraint on consents that only allows
    (person, term) when archived_at is null.

    This method archives one of the two active terms so
    that the combine merge method will be successful.
    """
    consents = Consent.objects.filter(person__in=[object_a, object_b])
    # Identify and group the active consents by term id
    active_consents_by_term_id = defaultdict(list)
    for consent in consents:
        if consent.archived_at is None:
            active_consents_by_term_id[consent.term_id].append(consent)

    # archive least recent active consents
    consents_to_archive = []
    consents_to_recreate = []
    for term_consents in active_consents_by_term_id.values():
        if len(term_consents) < 2:
            continue
        consent_a, consent_b = term_consents[0], term_consents[1]
        if consent_a.created_at < consent_b.created_at:
            consents_to_archive.append(consent_a)
        elif consent_b.created_at < consent_a.created_at:
            consents_to_archive.append(consent_b)
        else:
            # If they were created at the same time rather than being
            # nondeterministic archive both and when the user logs in again
            # they can consent to the term once more.
            consents_to_archive.append(consent_a)
            consents_to_archive.append(consent_b)
            consents_to_recreate.append(
                Consent(
                    person=base_obj,
                    term=consent_a.term,
                    term_option=None,
                )
            )
    Consent.objects.filter(pk__in=[c.pk for c in consents_to_archive]).update(
        archived_at=timezone.now()
    )
    Consent.objects.bulk_create(consents_to_recreate)


def merge_objects(
    object_a, object_b, easy_fields, difficult_fields, choices, base_a=True
):
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
            if value == "obj_a":
                setattr(base_obj, attr, getattr(object_a, attr))
            elif value == "obj_b":
                setattr(base_obj, attr, getattr(object_b, attr))
            elif value == "combine":
                try:
                    new_value = getattr(object_a, attr) + getattr(object_b, attr)
                    setattr(base_obj, attr, new_value)
                except TypeError:
                    # probably 'unsupported operand type', but we
                    # can't do much about it…
                    pass

        for attr in difficult_fields:
            if attr == "comments":
                # special case handled below the for-loop
                continue

            related_a = getattr(object_a, attr)
            related_b = getattr(object_b, attr)

            manager = getattr(base_obj, attr)
            value = choices.get(attr)

            # switch only if this is opposite object
            if value == "obj_a" and manager != related_a:
                if hasattr(manager, "clear"):
                    # M2M and FK with `null=True` have `.clear()` method
                    # which unassigns instead of removing the related objects
                    manager.clear()
                else:
                    # in some cases FK are strictly related with the instance
                    # ie. they cannot be unassigned (`null=False`), so the
                    # only sensible solution is to remove them
                    manager.all().delete()
                manager.set(list(related_a.all()))

            elif value == "obj_b" and manager != related_b:
                if hasattr(manager, "clear"):
                    # M2M and FK with `null=True` have `.clear()` method
                    # which unassigns instead of removing the related objects
                    manager.clear()
                else:
                    # in some cases FK are strictly related with the instance
                    # ie. they cannot be unassigned (`null=False`), so the
                    # only sensible solution is to remove them
                    manager.all().delete()
                manager.set(list(related_b.all()))

            elif value == "obj_a" and manager == related_a:
                # since we're keeping current values, try to remove (or clear
                # if possible) opposite (obj_b) - they may not be removable
                # via on_delete=CASCADE, so try manually
                if hasattr(related_b, "clear"):
                    related_b.clear()
                else:
                    related_b.all().delete()

            elif value == "obj_b" and manager == related_b:
                # since we're keeping current values, try to remove (or clear
                # if possible) opposite (obj_a) - they may not be removable
                # via on_delete=CASCADE, so try manually
                if hasattr(related_a, "clear"):
                    related_a.clear()
                else:
                    related_a.all().delete()

            elif value == "combine":
                to_add = None
                if attr == "consent_set":
                    archive_least_recent_active_consents(object_a, object_b, base_obj)

                if manager == related_a:
                    to_add = related_b.all()
                if manager == related_b:
                    to_add = related_a.all()

                # Some entries may cause IntegrityError (violation of
                # uniqueness constraint) because they are duplicates *after*
                # being added by the manager.
                # In this case they must be removed to not cause
                # on_delete=PROTECT violation after merging
                # (merging_obj.delete()).
                for element in to_add:
                    try:
                        with transaction.atomic():
                            manager.add(element)
                    except IntegrityError:
                        try:
                            element.delete()
                        except IntegrityError as e:
                            integrity_errors.append(str(e))

        if "comments" in choices:
            value = choices["comments"]
            # special case: comments made regarding these objects
            comments_a = Comment.objects.for_model(object_a)
            comments_b = Comment.objects.for_model(object_b)
            base_obj_ct = ContentType.objects.get_for_model(base_obj)

            if value == "obj_a":
                # we're keeping comments on obj_a, and removing (hiding)
                # comments on obj_b
                # WARNING: sequence of operations is important here!
                comments_b.update(is_removed=True)
                comments_a.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )

            elif value == "obj_b":
                # we're keeping comments on obj_b, and removing (hiding)
                # comments on obj_a
                # WARNING: sequence of operations is important here!
                comments_a.update(is_removed=True)
                comments_b.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )

            elif value == "combine":
                # we're making comments from either of the objects point to
                # the new base object
                comments_a.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )
                comments_b.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )

        merging_obj.delete()

        return base_obj.save(), integrity_errors


def redirect_with_next_support(request, *args, **kwargs):
    """Works in the same way as `redirect` except when there is GET parameter
    named "next". In that case, user is redirected to the URL from that
    parameter. If you have a class-based view, use RedirectSupportMixin that
    does the same."""

    next_url = request.GET.get("next", None)
    if next_url is not None and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts=settings.ALLOWED_HOSTS
    ):
        return redirect(next_url)
    else:
        return redirect(*args, **kwargs)


def dict_without_Nones(**keys):
    return {k: v for k, v in keys.items() if v is not None}


def str2bool(v):
    """Decoding string-encoded bool into Python objects.
    This function returns one of the following:
    * True if value decodes to true,
    * False if value decodes to false,
    * None otherwise.

    Based on: https://stackoverflow.com/a/715468"""
    value = str(v).lower()
    if value in ("yes", "true", "t", "1"):
        return True
    elif value in ("no", "false", "f", "0"):
        return False
    else:
        return None


def choice_field_with_other(choices, default, verbose_name=None, help_text=None):
    assert default in [c[0] for c in choices]
    assert all(c[0] != "" for c in choices)

    field = models.CharField(
        max_length=STR_MED,
        choices=choices,
        verbose_name=verbose_name,
        help_text=help_text,
        null=False,
        blank=False,
        default=default,
    )
    other_field = models.CharField(
        max_length=STR_LONG,
        verbose_name=" ",
        null=False,
        blank=True,
        default="",
    )
    return field, other_field


def match_notification_email(obj):
    """Try to match applied object to a set of criteria (defined in
    `settings.py`)."""
    results = []

    # some objects may not have this attribute, in this case we should fall
    # back to default criteria email
    if hasattr(obj, "country") and obj.country:
        results = Criterium.objects.filter(countries__contains=obj.country).values_list(
            "email", flat=True
        )
    else:
        # use general notification criteria when event has no country
        results = [settings.ADMIN_NOTIFICATION_CRITERIA_DEFAULT]

    # fallback to default address if nothing matches
    return results or [settings.ADMIN_NOTIFICATION_CRITERIA_DEFAULT]


def add_comment(content_object, comment, **kwargs):
    """A simple way to create a comment for specific object."""
    user = kwargs.get("user", None)
    user_name = kwargs.get("user_name", "Automatic comment")
    submit_date = kwargs.get(
        "submit_date", datetime.datetime.now(datetime.timezone.utc)
    )
    site = kwargs.get("site", Site.objects.get_current())

    return Comment.objects.create(
        comment=comment,
        content_object=content_object,
        user=user,
        user_name=user_name,
        submit_date=submit_date,
        site=site,
    )


def reports_link_hash(slug: str) -> str:
    """Generate hash for accessing workshop reports repository."""
    lowered = slug.lower()
    salt_front = settings.REPORTS_SALT_FRONT
    salt_back = settings.REPORTS_SALT_BACK
    hashed = sha1(f"{salt_front}{lowered}{salt_back}".encode("utf-8"))
    return hashed.hexdigest()


def reports_link(slug: str) -> str:
    """Return link to workshop's reports with hash and slug filled in."""
    hashed = reports_link_hash(slug)
    link = settings.REPORTS_LINK
    return link.format(hash=hashed, slug=slug)
