from dataclasses import dataclass
from datetime import date, datetime, time
from functools import partial
import json
import re
from typing import Any, Optional, TypedDict, cast

import requests
from rest_framework.utils.encoders import JSONEncoder
import yaml

from workshops.exceptions import WrongWorkshopURL
from workshops.models import Event

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


class WorkshopMetadata(TypedDict):
    slug: str
    language: str
    start: date | None
    end: date | None
    country: str
    venue: str
    address: str
    latitude: float | None
    longitude: float | None
    reg_key: int | None
    instructors: list[str]
    helpers: list[str]
    contact: list[str]


@dataclass
class Requirement:
    name: str
    display: str | None
    required: bool
    match_format: str | None

    @property
    def display_name(self) -> str:
        if self.display:
            return f"{self.display} {self.name}"
        return self.name


def fetch_workshop_metadata(event_url: str, timeout: int = 5) -> dict[str, str]:
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


def generate_url_to_event_index(website_url: str) -> tuple[str, str]:
    """Given URL to workshop's website, generate a URL to its raw `index.html`
    file in GitHub repository."""
    template = "https://raw.githubusercontent.com/{name}/{repo}" "/gh-pages/index.html"

    for regex in [Event.WEBSITE_REGEX, Event.REPO_REGEX]:
        results = regex.match(website_url)
        if results:
            return template.format(**results.groupdict()), results.group("repo")
    raise WrongWorkshopURL("URL doesn't match Github website or repo format.")


def find_workshop_YAML_metadata(content: str) -> dict[str, str]:
    """Given workshop's raw `index.html`, find and take YAML metadata that
    have workshop-related data."""
    try:
        _, header, _ = content.split("---")
        metadata = yaml.load(header.strip(), Loader=yaml.SafeLoader)
    except (ValueError, yaml.YAMLError):
        # can't unpack or header is not YML format
        return dict()

    # get metadata to the form returned by `find_workshop_HTML_metadata`
    # because YAML tries to interpret values from index's header
    filtered_metadata = {key: value for key, value in metadata.items() if key in ALLOWED_METADATA_NAMES}
    for key, value in filtered_metadata.items():
        if isinstance(value, int) or isinstance(value, float):
            filtered_metadata[key] = str(value)
        elif isinstance(value, date):
            filtered_metadata[key] = "{:%Y-%m-%d}".format(value)
        elif isinstance(value, list):
            filtered_metadata[key] = "|".join(value)

    return filtered_metadata


def find_workshop_HTML_metadata(content: str) -> dict[str, str]:
    """Given website content, find and take <meta> metadata that have
    workshop-related data."""

    R = r'<meta\s+name="(?P<name>\w+?)"\s+content="(?P<content>.*?)"\s*?/?>'
    regexp = re.compile(R)

    return {name: content for name, content in regexp.findall(content) if name in ALLOWED_METADATA_NAMES}


def parse_workshop_metadata(metadata: dict[str, str]) -> WorkshopMetadata:
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
        metadata_lat: Optional[str] = metadata.get("lat", "")
        metadata_lng: Optional[str] = metadata.get("lng", "")
    else:
        try:
            metadata_lat, metadata_lng = metadata.get("latlng", "").split(",")
        except (ValueError, AttributeError):
            metadata_lat, metadata_lng = None, None

    try:
        latitude: Optional[float] = float(metadata_lat.strip())  # type: ignore
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        latitude = None
    try:
        longitude: Optional[float] = float(metadata_lng.strip())  # type: ignore
    except (ValueError, AttributeError):
        # value error: can't convert string to float
        # attribute error: object doesn't have "split" or "strip" methods
        longitude = None

    try:
        reg_key_str = metadata.get("eventbrite", "")
        reg_key = int(reg_key_str)
    except (ValueError, TypeError):
        # value error: can't convert string to int
        # type error: can't convert None to int
        reg_key = None

    try:
        start_str = metadata.get("startdate", "")
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
    except ValueError:
        start = None

    try:
        end_str = metadata.get("enddate", "")
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
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


def validate_workshop_metadata(metadata: WorkshopMetadata) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

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
        name_ = requirement.display_name
        required_ = requirement.required
        type_ = "required" if required_ else "optional"
        value_ = metadata.get(requirement.name)

        if value_ is None:
            issues = errors if required_ else warnings
            issues.append(f"Missing {type_} metadata {name_}.")
        elif value_ == "FIXME":
            errors.append(f'Placeholder value "FIXME" for {type_} metadata {name_}.')
        else:
            try:
                if (required_ or value_) and requirement.match_format is not None:
                    if not re.match(requirement.match_format, str(value_)):
                        errors.append(
                            f'Invalid value "{value_}" for {type_} metadata {name_}: should be'
                            f' in format "{requirement.match_format}".'
                        )
            except (re.error, TypeError):
                pass

    return errors, warnings


def datetime_match(string: str) -> date | time | str:
    """Convert string date/datetime/time to date/datetime/time."""
    formats = (
        # date
        ("%Y-%m-%d", "date"),
        # datetime (no microseconds, timezone unaware)
        ("%Y-%m-%dT%H:%M:%S", None),
        # datetime (w/ microseconds, timezone unaware)
        ("%Y-%m-%dT%H:%M:%S.%f", None),
        # time (no microseconds, timezone unaware)
        ("%H:%M:%S", "time"),
        # try parsing time (w/ microseconds, timezone unaware)
        ("%H:%M:%S.%f", "time"),
    )
    for format_, method in formats:
        try:
            v = datetime.strptime(string, format_)
            if method is not None:
                return cast(date | time, getattr(v, method)())
            return v
        except ValueError:
            pass

    # TODO: Implement timezone-aware datetime parsing (currently
    #       not available because datetime.datetime.strptime
    #       doesn't support "+HH:MM" format [only "+HHMM"]; nor
    #       does it support "Z" at the end)

    return string


def datetime_decode[T1: dict[Any, Any], T2: list[Any]](obj: T1 | T2 | str) -> T1 | T2 | date | time | str:
    """Recursively call for each iterable, and try to decode each string."""
    if isinstance(obj, dict) or isinstance(obj, list):
        iterator = obj.items if isinstance(obj, dict) else partial(enumerate, obj)
        for k, item in iterator():
            if isinstance(item, str):
                obj[k] = datetime_match(item)

            elif isinstance(item, list) or isinstance(item, dict):
                # recursive call
                obj[k] = datetime_decode(item)

        return obj  # type: ignore

    elif isinstance(obj, str):
        return datetime_match(obj)

    else:
        return obj


def metadata_serialize(obj: Any) -> str:
    """Serialize object to be put in the database."""
    return json.dumps(obj, cls=JSONEncoder)


def metadata_deserialize(obj: str) -> Any:
    """Deserialize object from the database."""
    objs = json.loads(obj)
    # convert strings to datetimes (if they match format)
    return datetime_decode(objs)
