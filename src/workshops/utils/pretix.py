"""Read check-in (attendance) data from Pretix.

This module is intentionally split into layers so that parts of it can later move into a
separate worker (e.g. AWS Lambda):

1. `parse_pretix_event_url` + `PretixClient` - fetching data from the Pretix REST API.
2. `checked_in_attendees` / `session_blocks_by_subevent` - turning raw Pretix data into
   `PretixAttendee`s and `PretixSessionBlock`s.
3. `attendees_to_person_task_entries` - converting attendees into AMY's bulk-add entries.

Pretix API docs: https://docs.pretix.eu/dev/api/resources/orders.html
"""

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import urlparse

import requests
from django.conf import settings

from src.workshops.utils.person_upload import PersonTaskEntry

logger = logging.getLogger("amy")

# Orders in these states are valid: "p" = paid (includes free orders), "n" = pending.
# Canceled ("c") and expired ("e") orders are skipped.
VALID_ORDER_STATUSES = {"p", "n"}
DEFAULT_TIMEOUT_SECONDS = 15
# Upper bound on number of fetched pages, to avoid looping forever on a misbehaving server.
MAX_PAGES = 100


class PretixError(Exception):
    """Generic problem with getting data from Pretix."""


class PretixConfigurationError(PretixError):
    """Pretix integration is not configured (e.g. missing API token)."""


class PretixURLError(PretixError):
    """Provided URL doesn't point to a known Pretix event."""


@dataclass(frozen=True)
class PretixEventRef:
    organizer: str
    event: str
    subevent_id: int | None = None


@dataclass(frozen=True)
class PretixSessionBlock:
    """Part of a sub-event (event date) with its own check-in, e.g. one day of a multi-day training."""

    id: int
    date_from: datetime | None
    date_to: datetime | None
    location: str = ""


@dataclass(frozen=True)
class PretixCheckin:
    datetime: datetime | None
    session_block_id: int | None = None


@dataclass(frozen=True)
class PretixAttendee:
    personal: str
    family: str
    email: str | None
    order_code: str
    position_id: int
    order_email: str | None = None
    subevent_id: int | None = None
    checkins: tuple[PretixCheckin, ...] = ()


@dataclass(frozen=True)
class PretixAttendance:
    attendees: list[PretixAttendee]
    # sub-event ID -> its session blocks, ordered by start date
    session_blocks: dict[int, list[PretixSessionBlock]] = field(default_factory=dict)


def parse_pretix_event_url(url: str, base_url: str | None = None) -> PretixEventRef:
    """Parse a public Pretix event URL into organizer, event slug and optional sub-event ID.

    Supported formats:
    * https://pretix.carpentries.org/<organizer>/<event>/
    * https://pretix.carpentries.org/<organizer>/<event>/<subevent_id>/ (event series)

    The URL's host must match the configured Pretix host, so that the API token is never sent
    to an unknown server."""
    base_url = base_url or settings.PRETIX_URL
    url = url.strip()
    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)
    expected_host = urlparse(base_url).hostname
    if not parsed.hostname or parsed.hostname != expected_host:
        raise PretixURLError(f"URL must point to the Pretix server at {expected_host}.")

    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) == 2:
        organizer, event = segments
        return PretixEventRef(organizer=organizer, event=event)
    if len(segments) == 3 and segments[2].isdigit():
        organizer, event, subevent = segments
        return PretixEventRef(organizer=organizer, event=event, subevent_id=int(subevent))

    raise PretixURLError(
        "Could not recognise a Pretix event in this URL. Expected format: "
        f"{base_url.rstrip('/')}/<organizer>/<event>/ or .../<organizer>/<event>/<date ID>/"
    )


class PretixClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = (base_url or settings.PRETIX_URL).rstrip("/")
        self.token = token if token is not None else settings.PRETIX_API_TOKEN
        if not self.token:
            raise PretixConfigurationError("Pretix API token is not configured (AMY_PRETIX_API_TOKEN).")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token {self.token}", "Accept": "application/json"})

    def _event_url(self, event_ref: PretixEventRef) -> str:
        return f"{self.base_url}/api/v1/organizers/{event_ref.organizer}/events/{event_ref.event}/"

    def _get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            if status == 404:
                raise PretixError("Event not found in Pretix (or the API token has no access to it).") from exc
            if status in (401, 403):
                raise PretixError("Pretix rejected the API token.") from exc
            raise PretixError(f"Pretix API returned HTTP {status}.") from exc
        except ValueError as exc:
            # Must go before RequestException: requests' JSONDecodeError subclasses both.
            raise PretixError("Pretix API returned an invalid response.") from exc
        except requests.RequestException as exc:
            raise PretixError(f"Could not connect to Pretix: {exc}") from exc

    def _paginate(self, url: str, params: dict[str, str] | None = None) -> Iterator[dict[str, Any]]:
        next_url: str | None = url
        for _ in range(MAX_PAGES):
            if not next_url:
                return
            data = self._get(next_url, params=params)
            yield from cast(list[dict[str, Any]], data.get("results", []))
            next_url = data.get("next")
            params = None  # `next` URL already contains query parameters

        raise PretixError(f"Too many result pages returned by Pretix (more than {MAX_PAGES}).")

    def event(self, event_ref: PretixEventRef) -> dict[str, Any]:
        return self._get(self._event_url(event_ref))

    def subevents(self, event_ref: PretixEventRef) -> Iterator[dict[str, Any]]:
        return self._paginate(self._event_url(event_ref) + "subevents/")

    def orders(self, event_ref: PretixEventRef) -> Iterator[dict[str, Any]]:
        return self._paginate(self._event_url(event_ref) + "orders/")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


def _attendee_name(position: dict[str, Any]) -> tuple[str, str]:
    """Return (personal, family) names of the position's attendee.

    Pretix stores names according to the event's name scheme in `attendee_name_parts`; most
    schemes use `given_name` and `family_name`. Other schemes fall back to the full name."""
    parts = position.get("attendee_name_parts") or {}
    given = (parts.get("given_name") or "").strip()
    family = (parts.get("family_name") or "").strip()
    if given or family:
        return given, family
    return _split_full_name(position.get("attendee_name") or "")


def _entry_checkins(position: dict[str, Any]) -> tuple[PretixCheckin, ...]:
    # Older Pretix versions don't have a check-in `type`; those are always entries.
    checkins = [
        PretixCheckin(
            datetime=_parse_datetime(checkin.get("datetime")),
            session_block_id=checkin.get("session_block"),
        )
        for checkin in position.get("checkins") or []
        if checkin.get("type", "entry") == "entry"
    ]
    return tuple(sorted(checkins, key=lambda c: c.datetime or datetime.min.replace(tzinfo=UTC)))


def _normalize_email(email: str | None) -> str | None:
    return email.strip().lower() or None if email else None


def checked_in_attendees(orders: Iterable[dict[str, Any]], subevent_id: int | None = None) -> list[PretixAttendee]:
    """Extract attendees with at least one entry check-in from Pretix orders.

    Attendee email falls back to the order email only for single-position orders; when one
    person buys tickets for others, the order email doesn't identify the attendees."""
    attendees: list[PretixAttendee] = []
    for order in orders:
        if order.get("status") not in VALID_ORDER_STATUSES:
            continue

        order_email = _normalize_email(order.get("email"))
        positions = [p for p in order.get("positions") or [] if not p.get("canceled")]
        # Add-ons (e.g. a T-shirt) are separate positions attached to a main position.
        main_positions = [p for p in positions if not p.get("addon_to")]

        for position in main_positions:
            if subevent_id is not None and position.get("subevent") != subevent_id:
                continue
            checkins = _entry_checkins(position)
            if not checkins:
                continue

            email = _normalize_email(position.get("attendee_email"))
            if not email and len(main_positions) == 1:
                email = order_email

            personal, family = _attendee_name(position)
            attendees.append(
                PretixAttendee(
                    personal=personal,
                    family=family,
                    email=email,
                    order_code=order.get("code", ""),
                    position_id=position.get("id", 0),
                    order_email=order_email,
                    subevent_id=position.get("subevent"),
                    checkins=checkins,
                )
            )

    return attendees


def session_blocks_by_subevent(subevents: Iterable[dict[str, Any]]) -> dict[int, list[PretixSessionBlock]]:
    result: dict[int, list[PretixSessionBlock]] = {}
    for subevent in subevents:
        blocks = [
            PretixSessionBlock(
                id=block["id"],
                date_from=_parse_datetime(block.get("date_from")),
                date_to=_parse_datetime(block.get("date_to")),
                location=block.get("location") or "",
            )
            for block in subevent.get("session_blocks") or []
        ]
        result[subevent["id"]] = sorted(blocks, key=lambda b: b.date_from or datetime.min.replace(tzinfo=UTC))
    return result


def deduplicate_attendees(attendees: list[PretixAttendee]) -> list[PretixAttendee]:
    """Remove attendees with repeated emails (e.g. someone registered twice)."""
    seen_emails: set[str] = set()
    result: list[PretixAttendee] = []
    for attendee in attendees:
        if attendee.email:
            if attendee.email in seen_emails:
                continue
            seen_emails.add(attendee.email)
        result.append(attendee)
    return result


def _format_datetime(value: datetime | None) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC") if value else "unknown time"


def _format_session_block(block: PretixSessionBlock) -> str:
    if (
        block.date_from
        and block.date_to
        and block.date_from.astimezone(UTC).date() == block.date_to.astimezone(UTC).date()
    ):
        label = f"{block.date_from.astimezone(UTC):%Y-%m-%d %H:%M}–{block.date_to.astimezone(UTC):%H:%M} UTC"
    else:
        label = f"{_format_datetime(block.date_from)} – {_format_datetime(block.date_to)}"
    return f"{label} ({block.location})" if block.location else label


def attendee_notes(attendee: PretixAttendee, session_blocks: dict[int, list[PretixSessionBlock]]) -> list[str]:
    """Human-readable details about the attendee's Pretix order and check-ins."""
    order = f"Pretix order {attendee.order_code}"
    if attendee.order_email and attendee.order_email != attendee.email:
        order += f", purchased by {attendee.order_email}"
    notes = [order + "."]

    blocks = session_blocks.get(attendee.subevent_id, []) if attendee.subevent_id is not None else []
    if len(blocks) > 1:
        attended = {c.session_block_id for c in attendee.checkins if c.session_block_id is not None}
        notes.append(f"Checked in to {len(attended & {b.id for b in blocks})} of {len(blocks)} session blocks:")
        notes.extend(f"{'✔' if block.id in attended else '✘'} {_format_session_block(block)}" for block in blocks)
    else:
        notes.extend(f"Checked in at {_format_datetime(c.datetime)}." for c in attendee.checkins)

    return notes


def attendees_to_person_task_entries(
    attendees: list[PretixAttendee],
    event_slug: str,
    session_blocks: dict[int, list[PretixSessionBlock]] | None = None,
    role: str = "learner",
) -> list[PersonTaskEntry]:
    """Convert attendees into entries understood by the person bulk-add confirmation view."""
    return [
        PersonTaskEntry(
            personal=attendee.personal,
            family=attendee.family,
            username="",  # set in `verify_upload_person_task`
            email=attendee.email,
            airport_iata="",
            event=event_slug,
            role=role,
            errors=[],
            info=[],
            notes=attendee_notes(attendee, session_blocks or {}),
        )
        for attendee in attendees
    ]


def fetch_attendance(event_ref: PretixEventRef, client: PretixClient | None = None) -> PretixAttendance:
    client = client or PretixClient()
    attendees = deduplicate_attendees(checked_in_attendees(client.orders(event_ref), event_ref.subevent_id))

    session_blocks: dict[int, list[PretixSessionBlock]] = {}
    if attendees and client.event(event_ref).get("has_subevents"):
        session_blocks = session_blocks_by_subevent(client.subevents(event_ref))

    return PretixAttendance(attendees=attendees, session_blocks=session_blocks)
