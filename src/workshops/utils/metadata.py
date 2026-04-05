import json
from dataclasses import dataclass
from datetime import date, datetime, time
from functools import partial
from typing import Any, TypedDict, cast

from rest_framework.utils.encoders import JSONEncoder


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


def datetime_decode[T1: dict[Any, Any], T2: list[Any]](
    obj: T1 | T2 | str,
) -> T1 | T2 | date | time | str:
    """Recursively call for each iterable, and try to decode each string."""
    if isinstance(obj, (list, dict)):
        iterator = obj.items if isinstance(obj, dict) else partial(enumerate, obj)
        for k, item in iterator():
            if isinstance(item, str):
                obj[k] = datetime_match(item)

            elif isinstance(item, (list, dict)):
                # recursive call
                obj[k] = datetime_decode(item)

        return obj

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
