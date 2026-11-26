from datetime import UTC, date, datetime
from typing import Any

import requests_mock
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from src.workshops.models import Event, Organization, Person, Role, Task
from src.workshops.tests.base import TestBase
from src.workshops.utils.pretix import (
    PretixAttendee,
    PretixCheckin,
    PretixClient,
    PretixConfigurationError,
    PretixError,
    PretixEventRef,
    PretixSessionBlock,
    PretixURLError,
    attendee_notes,
    attendees_to_person_task_entries,
    checked_in_attendees,
    deduplicate_attendees,
    fetch_attendance,
    parse_pretix_event_url,
    session_blocks_by_subevent,
)

BASE_URL = "https://pretix.example.org"
EVENT_URL = f"{BASE_URL}/api/v1/organizers/carpentries/events/workshop/"
ORDERS_URL = f"{EVENT_URL}orders/"
SUBEVENTS_URL = f"{EVENT_URL}subevents/"
EVENT_REF = PretixEventRef(organizer="carpentries", event="workshop")


def make_position(
    id: int = 1,
    given: str = "Harry",
    family: str = "Potter",
    email: str | None = "harry@example.org",
    checkins: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if checkins is None:
        checkins = [{"list": 1, "type": "entry", "datetime": "2026-11-01T10:00:00Z"}]
    return {
        "id": id,
        "attendee_name": f"{given} {family}",
        "attendee_name_parts": {"_scheme": "given_family", "given_name": given, "family_name": family},
        "attendee_email": email,
        "checkins": checkins,
        "canceled": False,
        "addon_to": None,
        "subevent": None,
        **kwargs,
    }


def make_subevent(id: int = 52, blocks: list[tuple[int, str, str]] | None = None) -> dict[str, Any]:
    return {
        "id": id,
        "session_blocks": [
            {"id": block_id, "date_from": date_from, "date_to": date_to, "location": ""}
            for block_id, date_from, date_to in blocks or []
        ],
    }


FOUR_DAY_BLOCKS = [
    (62, "2026-12-01T09:00:00Z", "2026-12-01T15:00:00Z"),
    (63, "2026-12-02T09:00:00Z", "2026-12-02T15:00:00Z"),
    (64, "2026-12-03T09:00:00Z", "2026-12-03T15:00:00Z"),
    (65, "2026-12-04T09:00:00Z", "2026-12-04T15:00:00Z"),
]


def make_order(
    positions: list[dict[str, Any]], code: str = "ABC12", status: str = "p", email: str = "buyer@example.org"
) -> dict[str, Any]:
    return {"code": code, "status": status, "email": email, "positions": positions}


class TestParsePretixEventURL(SimpleTestCase):
    def test_event_url(self) -> None:
        self.assertEqual(
            parse_pretix_event_url(f"{BASE_URL}/carpentries/workshop/", base_url=BASE_URL),
            PretixEventRef("carpentries", "workshop"),
        )

    def test_event_series_url(self) -> None:
        self.assertEqual(
            parse_pretix_event_url(f"{BASE_URL}/carpentries/welcome/845/", base_url=BASE_URL),
            PretixEventRef("carpentries", "welcome", 845),
        )

    def test_url_without_scheme_or_trailing_slash(self) -> None:
        self.assertEqual(
            parse_pretix_event_url("pretix.example.org/carpentries/workshop", base_url=BASE_URL),
            PretixEventRef("carpentries", "workshop"),
        )

    def test_query_string_ignored(self) -> None:
        self.assertEqual(
            parse_pretix_event_url(f"{BASE_URL}/carpentries/workshop/?voucher=X", base_url=BASE_URL),
            PretixEventRef("carpentries", "workshop"),
        )

    def test_other_host_rejected(self) -> None:
        with self.assertRaises(PretixURLError):
            parse_pretix_event_url("https://evil.example.com/carpentries/workshop/", base_url=BASE_URL)

    def test_invalid_paths_rejected(self) -> None:
        for path in ["", "carpentries/", "carpentries/workshop/not-a-number/", "a/b/1/2/"]:
            with self.subTest(path=path), self.assertRaises(PretixURLError):
                parse_pretix_event_url(f"{BASE_URL}/{path}", base_url=BASE_URL)


class TestCheckedInAttendees(SimpleTestCase):
    def test_only_checked_in_positions(self) -> None:
        orders = [
            make_order([make_position(id=1)], code="A"),
            make_order([make_position(id=2, given="Ron", email="ron@example.org", checkins=[])], code="B"),
        ]
        self.assertEqual(
            checked_in_attendees(iter(orders)),
            [
                PretixAttendee(
                    "Harry",
                    "Potter",
                    "harry@example.org",
                    "A",
                    1,
                    order_email="buyer@example.org",
                    checkins=(PretixCheckin(datetime(2026, 11, 1, 10, tzinfo=UTC)),),
                )
            ],
        )

    def test_exit_only_checkins_ignored(self) -> None:
        orders = [make_order([make_position(checkins=[{"list": 1, "type": "exit"}])])]
        self.assertEqual(checked_in_attendees(iter(orders)), [])

    def test_checkin_without_type_counts_as_entry(self) -> None:
        orders = [make_order([make_position(checkins=[{"list": 1}])])]
        self.assertEqual(len(checked_in_attendees(iter(orders))), 1)

    def test_canceled_and_expired_orders_skipped(self) -> None:
        orders = [make_order([make_position()], status="c"), make_order([make_position()], status="e")]
        self.assertEqual(checked_in_attendees(iter(orders)), [])

    def test_pending_order_included(self) -> None:
        orders = [make_order([make_position()], status="n")]
        self.assertEqual(len(checked_in_attendees(iter(orders))), 1)

    def test_canceled_positions_and_addons_skipped(self) -> None:
        orders = [
            make_order(
                [
                    make_position(id=1),
                    make_position(id=2, given="Ron", canceled=True),
                    make_position(id=3, given="T-shirt", addon_to=1),
                ]
            )
        ]
        self.assertEqual([a.position_id for a in checked_in_attendees(iter(orders))], [1])

    def test_subevent_filter(self) -> None:
        orders = [make_order([make_position(id=1, subevent=10), make_position(id=2, subevent=11)])]
        self.assertEqual([a.position_id for a in checked_in_attendees(iter(orders), subevent_id=11)], [2])

    def test_order_email_fallback_for_single_position(self) -> None:
        orders = [make_order([make_position(email=None)], email="Buyer@Example.org ")]
        self.assertEqual(checked_in_attendees(iter(orders))[0].email, "buyer@example.org")

    def test_no_order_email_fallback_for_multiple_positions(self) -> None:
        orders = [make_order([make_position(id=1, email=None), make_position(id=2, given="Ron", email=None)])]
        self.assertEqual([a.email for a in checked_in_attendees(iter(orders))], [None, None])

    def test_checkins_with_session_blocks(self) -> None:
        checkins = [
            {"list": 1, "type": "entry", "datetime": "2026-12-04T09:05:00Z", "session_block": 65},
            {"list": 1, "type": "entry", "datetime": "2026-12-02T09:05:00Z", "session_block": 63},
            {"list": 1, "type": "exit", "datetime": "2026-12-02T15:00:00Z", "session_block": 63},
        ]
        attendee = checked_in_attendees(iter([make_order([make_position(checkins=checkins, subevent=52)])]))[0]
        self.assertEqual(attendee.subevent_id, 52)
        self.assertEqual([c.session_block_id for c in attendee.checkins], [63, 65])  # sorted, entries only

    def test_name_fallback_to_full_name(self) -> None:
        position = make_position()
        position["attendee_name_parts"] = {"_scheme": "full", "full_name": "Hermione Jean Granger"}
        position["attendee_name"] = "Hermione Jean Granger"
        attendee = checked_in_attendees(iter([make_order([position])]))[0]
        self.assertEqual((attendee.personal, attendee.family), ("Hermione Jean", "Granger"))

    def test_deduplicate_by_email(self) -> None:
        attendees = [
            PretixAttendee("Harry", "Potter", "harry@example.org", "A", 1),
            PretixAttendee("Harry", "Potter", "harry@example.org", "B", 2),
            PretixAttendee("No", "Email", None, "C", 3),
            PretixAttendee("No", "Email", None, "D", 4),
        ]
        self.assertEqual([a.position_id for a in deduplicate_attendees(attendees)], [1, 3, 4])

    def test_attendees_to_person_task_entries(self) -> None:
        entries = attendees_to_person_task_entries(
            [PretixAttendee("Harry", "Potter", "harry@example.org", "A", 1)], "2026-11-01-test"
        )
        self.assertEqual(
            entries,
            [
                {
                    "personal": "Harry",
                    "family": "Potter",
                    "username": "",
                    "email": "harry@example.org",
                    "airport_iata": "",
                    "event": "2026-11-01-test",
                    "role": "learner",
                    "errors": [],
                    "info": [],
                    "notes": ["Pretix order A."],
                }
            ],
        )


class TestSessionBlocksAndNotes(SimpleTestCase):
    def test_session_blocks_by_subevent(self) -> None:
        blocks = session_blocks_by_subevent([make_subevent(52, list(reversed(FOUR_DAY_BLOCKS))), make_subevent(53)])
        self.assertEqual([b.id for b in blocks[52]], [62, 63, 64, 65])
        self.assertEqual(blocks[52][0].date_from, datetime(2026, 12, 1, 9, tzinfo=UTC))
        self.assertEqual(blocks[53], [])

    def test_notes_with_multiple_session_blocks(self) -> None:
        attendee = PretixAttendee(
            "Harry",
            "Potter",
            "harry@example.org",
            "J0HVT",
            30,
            order_email="harry@example.org",
            subevent_id=52,
            checkins=(PretixCheckin(None, 63), PretixCheckin(None, 65)),
        )
        blocks = session_blocks_by_subevent([make_subevent(52, FOUR_DAY_BLOCKS)])
        self.assertEqual(
            attendee_notes(attendee, blocks),
            [
                "Pretix order J0HVT.",
                "Checked in to 2 of 4 session blocks:",
                "✘ 2026-12-01 09:00–15:00 UTC",
                "✔ 2026-12-02 09:00–15:00 UTC",
                "✘ 2026-12-03 09:00–15:00 UTC",
                "✔ 2026-12-04 09:00–15:00 UTC",
            ],
        )

    def test_notes_without_session_blocks(self) -> None:
        attendee = PretixAttendee(
            "Ron",
            "Weasley",
            None,
            "V0EPZ",
            28,
            order_email="buyer@example.org",
            subevent_id=53,
            checkins=(PretixCheckin(datetime(2026, 11, 21, 15, 28, 42, tzinfo=UTC)),),
        )
        self.assertEqual(
            attendee_notes(attendee, {53: []}),
            ["Pretix order V0EPZ, purchased by buyer@example.org.", "Checked in at 2026-11-21 15:28 UTC."],
        )

    def test_single_session_block_shown_as_checkin_time(self) -> None:
        attendee = PretixAttendee(
            "Ron", "Weasley", "ron@example.org", "A", 1, subevent_id=52, checkins=(PretixCheckin(None, 62),)
        )
        blocks = {52: [PretixSessionBlock(62, None, None)]}
        self.assertEqual(attendee_notes(attendee, blocks), ["Pretix order A.", "Checked in at unknown time."])


class TestPretixClient(SimpleTestCase):
    def test_missing_token(self) -> None:
        with self.assertRaises(PretixConfigurationError):
            PretixClient(base_url=BASE_URL, token="")

    def test_no_proxy_by_default(self) -> None:
        client = PretixClient(base_url=BASE_URL, token="secret")
        self.assertEqual(client.session.proxies, {})

    @override_settings(PRETIX_PROXY="http://localhost:1055")
    def test_proxy_configured(self) -> None:
        client = PretixClient(base_url=BASE_URL, token="secret")
        self.assertEqual(client.session.proxies, {"http": "http://localhost:1055", "https": "http://localhost:1055"})

    def test_pagination_and_auth_header(self) -> None:
        client = PretixClient(base_url=BASE_URL, token="secret")
        with requests_mock.Mocker() as mock:
            mock.get(
                ORDERS_URL,
                [
                    {"json": {"results": [make_order([make_position(id=1)])], "next": f"{ORDERS_URL}?page=2"}},
                    {"json": {"results": [make_order([make_position(id=2, email="ron@example.org")])], "next": None}},
                ],
            )
            mock.get(EVENT_URL, json={"has_subevents": False})
            attendance = fetch_attendance(EVENT_REF, client=client)

        self.assertEqual([a.position_id for a in attendance.attendees], [1, 2])
        self.assertEqual(attendance.session_blocks, {})
        self.assertEqual(mock.call_count, 3)
        self.assertEqual(mock.request_history[0].headers["Authorization"], "Token secret")

    def test_fetch_attendance_with_subevents(self) -> None:
        client = PretixClient(base_url=BASE_URL, token="secret")
        with requests_mock.Mocker() as mock:
            mock.get(ORDERS_URL, json={"results": [make_order([make_position(subevent=52)])], "next": None})
            mock.get(EVENT_URL, json={"has_subevents": True})
            mock.get(SUBEVENTS_URL, json={"results": [make_subevent(52, FOUR_DAY_BLOCKS)], "next": None})
            attendance = fetch_attendance(EVENT_REF, client=client)

        self.assertEqual([b.id for b in attendance.session_blocks[52]], [62, 63, 64, 65])

    def test_fetch_attendance_skips_event_lookup_without_attendees(self) -> None:
        client = PretixClient(base_url=BASE_URL, token="secret")
        with requests_mock.Mocker() as mock:
            mock.get(ORDERS_URL, json={"results": [], "next": None})
            attendance = fetch_attendance(EVENT_REF, client=client)

        self.assertEqual(attendance.attendees, [])
        self.assertEqual(mock.call_count, 1)

    def test_http_errors(self) -> None:
        client = PretixClient(base_url=BASE_URL, token="secret")
        for status, message in [(404, "not found"), (401, "rejected"), (500, "HTTP 500")]:
            with self.subTest(status=status), requests_mock.Mocker() as mock:
                mock.get(ORDERS_URL, status_code=status)
                with self.assertRaisesRegex(PretixError, message):
                    list(client.orders(EVENT_REF))

    def test_invalid_json(self) -> None:
        client = PretixClient(base_url=BASE_URL, token="secret")
        with requests_mock.Mocker() as mock:
            mock.get(ORDERS_URL, text="<html>")
            with self.assertRaisesRegex(PretixError, "invalid response"):
                list(client.orders(EVENT_REF))


@override_settings(
    PRETIX_URL=BASE_URL,
    PRETIX_API_TOKEN="secret",
    FLAGS={"PRETIX_ATTENDANCE": [("boolean", True)]},
)
class TestEventPretixAttendanceView(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self.event = Event.objects.create(
            slug="2026-11-01-pretix",
            host=Organization.objects.create(domain="pretix-host.example.org", fullname="Pretix Host"),
            start=date(2026, 11, 1),
        )
        self.url = reverse("event_pretix_attendance", args=[self.event.slug])

    def test_get(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @override_settings(FLAGS={"PRETIX_ATTENDANCE": [("boolean", False)]})
    def test_flag_disabled(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_unknown_event(self) -> None:
        response = self.client.get(reverse("event_pretix_attendance", args=["unknown"]))
        self.assertEqual(response.status_code, 404)

    def test_invalid_url(self) -> None:
        response = self.client.post(self.url, {"pretix_url": "https://example.com/a/b/"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("pretix_url", response.context["form"].errors)

    def test_pretix_error_shown(self) -> None:
        with requests_mock.Mocker() as mock:
            mock.get(ORDERS_URL, status_code=404)
            response = self.client.post(self.url, {"pretix_url": f"{BASE_URL}/carpentries/workshop/"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("not found", str(response.context["form"].non_field_errors()))

    def test_no_attendees(self) -> None:
        with requests_mock.Mocker() as mock:
            mock.get(ORDERS_URL, json={"results": [], "next": None})
            response = self.client.post(self.url, {"pretix_url": f"{BASE_URL}/carpentries/workshop/"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No checked-in attendees")
        self.assertIsNone(self.client.session.get("bulk-add-people"))

    def test_attendees_go_to_bulk_add_confirmation_and_can_be_saved(self) -> None:
        existing = Person.objects.create(
            personal="Harry", family="Potter", username="potter_harry_2", email="harry.potter@example.org"
        )
        # Regression: attendees without email must not be matched to a person without email.
        no_email_person = Person.objects.create(personal="Buyer", family="NoEmail", username="buyer_noemail")
        orders = [
            make_order([make_position(id=1, email="harry.potter@example.org")], code="A"),
            make_order([make_position(id=2, given="Luna", family="Lovegood", email="luna@example.org")], code="B"),
            # One buyer, two attendees without their own emails.
            make_order(
                [
                    make_position(id=3, given="Neville", family="Longbottom", email=None),
                    make_position(id=4, given="Dean", family="Thomas", email=None),
                ],
                code="C",
            ),
        ]
        with requests_mock.Mocker() as mock:
            mock.get(ORDERS_URL, json={"results": orders, "next": None})
            mock.get(EVENT_URL, json={"has_subevents": False})
            response = self.client.post(self.url, {"pretix_url": f"{BASE_URL}/carpentries/workshop/"})

        self.assertRedirects(response, reverse("person_bulk_add_confirmation"))
        session_entries = self.client.session["bulk-add-people"]
        self.assertEqual(
            [e["email"] for e in session_entries], ["harry.potter@example.org", "luna@example.org", None, None]
        )

        # Confirmation page matches the existing person by email.
        response = self.client.get(reverse("person_bulk_add_confirmation"))
        self.assertEqual(response.status_code, 200)
        entries = response.context["persons_tasks"]
        self.assertEqual(entries[0]["existing_person_id"], existing.pk)
        self.assertEqual([e["person_exists"] for e in entries], [True, False, False, False])
        self.assertEqual([e["personal"] for e in entries], ["Harry", "Luna", "Neville", "Dean"])
        self.assertFalse(response.context["any_errors"])
        self.assertContains(response, "Pretix order C, purchased by buyer@example.org.")

        # Confirm: learner tasks are created for both attendees.
        data = {
            "personal": [e["personal"] for e in entries],
            "family": [e["family"] for e in entries],
            "username": [e["username"] for e in entries],
            "email": [e["email"] or "" for e in entries],
            "airport_iata": [e["airport_iata"] for e in entries],
            "event": [e["event"] for e in entries],
            "role": [e["role"] for e in entries],
            "confirm": "Confirm",
        }
        self.client.post(reverse("person_bulk_add_confirmation"), {**data, "confirm": "", "verify": "Verify"})
        # Notes survive the edit/verify round-trip.
        self.assertEqual(
            self.client.session["bulk-add-people"][2]["notes"][0], "Pretix order C, purchased by buyer@example.org."
        )
        self.client.post(reverse("person_bulk_add_confirmation"), data)

        learner = Role.objects.get(name="learner")
        self.assertTrue(Task.objects.filter(event=self.event, person=existing, role=learner).exists())
        self.assertTrue(Task.objects.filter(event=self.event, person__email="luna@example.org", role=learner).exists())
        for personal, family in [("Neville", "Longbottom"), ("Dean", "Thomas")]:
            self.assertTrue(
                Task.objects.filter(event=self.event, person__personal=personal, person__family=family).exists()
            )
        self.assertFalse(Task.objects.filter(person=no_email_person).exists())
