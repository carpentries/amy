from datetime import date, datetime, time, timedelta
from typing import Any
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from src.consents.models import Consent, Term
from src.workshops.exceptions import InternalError
from src.workshops.models import Event, Language, Organization, Person, WorkshopRequest
from src.workshops.tests.base import TestBase
from src.workshops.utils.consents import archive_least_recent_active_consents
from src.workshops.utils.dates import human_daterange
from src.workshops.utils.emails import match_notification_email
from src.workshops.utils.feature_flags import feature_flag_enabled
from src.workshops.utils.metadata import (
    datetime_decode,
    datetime_match,
    metadata_deserialize,
    metadata_serialize,
)
from src.workshops.utils.pagination import Paginator
from src.workshops.utils.reports import reports_link, reports_link_hash
from src.workshops.utils.urls import safe_next_or_default_url
from src.workshops.utils.usernames import create_username
from src.workshops.utils.views import assign


class TestHandlingEventMetadata(TestBase):
    maxDiff = None

    html_content = """
<html><head>
<meta name="slug" content="2015-07-13-test" />
<meta name="startdate" content="2015-07-13" />
<meta name="enddate" content="2015-07-14" />
<meta name="country" content="us" />
<meta name="venue" content="Euphoric State University" />
<meta name="address" content="Highway to Heaven 42, Academipolis" />
<meta name="latlng" content="36.998977, -109.045173" />
<meta name="language" content="us" />
<meta name="invalid" content="invalid" />
<meta name="instructor" content="Hermione Granger|Ron Weasley" />
<meta name="helper" content="Peter Parker|Tony Stark|Natasha Romanova" />
<meta name="contact" content="hermione@granger.co.uk|rweasley@ministry.gov" />
<meta name="eventbrite" content="10000000" />
<meta name="charset" content="utf-8" />
</head>
<body>
<h1>test</h1>
</body></html>
"""
    yaml_content = """---
layout: workshop
root: .
venue: Euphoric State University
address: Highway to Heaven 42, Academipolis
country: us
language: us
latlng: 36.998977, -109.045173
humandate: Jul 13-14, 2015
humantime: 9:00 - 17:00
startdate: 2015-07-13
enddate: "2015-07-14"
instructor: ["Hermione Granger", "Ron Weasley",]
helper: ["Peter Parker", "Tony Stark", "Natasha Romanova",]
contact: ["hermione@granger.co.uk", "rweasley@ministry.gov"]
etherpad:
eventbrite: 10000000
----
Other content.
"""
    date_serialization_tests = [
        # simple tests
        ("", ""),
        ("empty string", "empty string"),
        # format-matching
        ("2016-04-18", date(2016, 4, 18)),
        ("2016-04-18T16:41:30", datetime(2016, 4, 18, 16, 41, 30)),
        ("2016-04-18T16:41:30.123", datetime(2016, 4, 18, 16, 41, 30, 123000)),
        ("16:41:30", time(16, 41, 30)),
        ("16:41:30.123", time(16, 41, 30, 123000)),
        # format not matching (ie. timezone-aware)
        ("2016-04-18T16:41:30+02:00", "2016-04-18T16:41:30+02:00"),
        ("2016-04-18T14:41:30Z", "2016-04-18T14:41:30Z"),
        ("16:41:30+02:00", "16:41:30+02:00"),
        ("14:41:30Z", "14:41:30Z"),
    ]
    expected_metadata_parsed = {
        "slug": "2015-07-13-test",
        "language": "US",
        "start": date(2015, 7, 13),
        "end": date(2015, 7, 14),
        "country": "US",
        "venue": "Euphoric State University",
        "address": "Highway to Heaven 42, Academipolis",
        "latitude": 36.998977,
        "longitude": -109.045173,
        "reg_key": 10000000,
        "instructors": ["Hermione Granger", "Ron Weasley"],
        "helpers": ["Peter Parker", "Tony Stark", "Natasha Romanova"],
        "contact": ["hermione@granger.co.uk", "rweasley@ministry.gov"],
    }

    def test_metadata_serialization(self) -> None:
        # Act
        serialized_json = metadata_serialize(self.expected_metadata_parsed)
        # Assert
        self.assertIn("2015-07-13", serialized_json)
        self.assertIn("2015-07-14", serialized_json)
        self.assertIn("2015-07-13-test", serialized_json)
        self.assertIn("-109.045173", serialized_json)
        self.assertIn("36.998977", serialized_json)
        self.assertIn('["hermione@granger.co.uk", "rweasley@ministry.gov"]', serialized_json)

    def test_metadata_serialization_deserialization(self) -> None:
        # Act
        serialized_json = metadata_serialize(self.expected_metadata_parsed)
        deserialized_data = metadata_deserialize(serialized_json)
        # Assert
        self.assertNotEqual(serialized_json, deserialized_data)
        self.assertEqual(deserialized_data, self.expected_metadata_parsed)

    def test_metadata_deserialization_of_string(self) -> None:
        "Ensure datetime matching function works correctly for strings."
        for test, expected in self.date_serialization_tests:
            # Act
            result = datetime_match(test)
            # Assert
            self.assertEqual(result, expected)

    def test_metadata_deserialization_of_list(self) -> None:
        """Ensure our datetime matching function works correctly for lists."""
        # Arrange

        # Decompose self.date_serialization_tests into lists of values from first
        # and second column.
        tests = [v[0] for v in self.date_serialization_tests]
        expected = [v[1] for v in self.date_serialization_tests]
        # Act
        result = datetime_decode(tests)
        # Assert
        self.assertEqual(result, expected)

    def test_metadata_deserialization_of_dict(self) -> None:
        """Ensure our datetime matching function works correctly for dicts."""
        # Arrange
        tests = {k: k for k, _ in self.date_serialization_tests}
        expected = {k: v for k, v in self.date_serialization_tests}
        # Act
        result = datetime_decode(tests)
        # Assert
        self.assertEqual(result, expected)

    def test_metadata_deserialization_of_nested(self) -> None:
        """Ensure our datetime matching function works correctly for nested
        objects/lists."""
        # Arrange
        dict_test = {"2016-04-18": "2016-04-18"}
        dict_expected = {"2016-04-18": date(2016, 4, 18)}
        test1 = [dict_test.copy(), dict_test.copy(), dict_test.copy()]
        expected1 = [dict_expected.copy(), dict_expected.copy(), dict_expected.copy()]
        test2 = {"1": test1[:]}
        expected2 = {"1": expected1[:]}

        # Act
        result1 = datetime_decode(test1)
        result2 = datetime_decode(test2)

        # Assert
        self.assertEqual(result1, expected1)
        self.assertEqual(result2, expected2)


class TestUsernameGeneration(TestBase):
    def setUp(self) -> None:
        Person.objects.create_user(
            username="potter_harry",
            personal="Harry",
            family="Potter",
            email="hp@ministry.gov",
        )

    def test_conflicting_name(self) -> None:
        """Ensure `create_username` works correctly when conflicting username
        already exists."""
        username = create_username(personal="Harry", family="Potter")
        self.assertEqual(username, "potter_harry_2")

    def test_nonconflicting_name(self) -> None:
        """Ensure `create_username` works correctly when there's no conflicts
        in the database."""
        username = create_username(personal="Hermione", family="Granger")
        self.assertEqual(username, "granger_hermione")

    def test_nonlatin_characters(self) -> None:
        """Ensure correct behavior for non-latin names."""
        username = create_username(personal="Grzegorz", family="Brzęczyszczykiewicz")
        self.assertEqual(username, "brzczyszczykiewicz_grzegorz")

    def test_reached_number_of_tries(self) -> None:
        """Ensure we don't DoS ourselves."""
        tries = 1
        with self.assertRaises(InternalError):
            create_username(personal="Harry", family="Potter", tries=tries)

    def test_hyphenated_name(self) -> None:
        """Ensure people with hyphens in names have correct usernames
        generated."""
        username = create_username(personal="Andy", family="Blanking-Crush")
        self.assertEqual(username, "blanking-crush_andy")

    def test_noned_names(self) -> None:
        """This is a regression test against #1682
        (https://github.com/carpentries/amy/issues/1682).

        The error was: family name was allowed to be null, which caused 500 errors
        when trying to save person without the family name due to name normalization."""
        username = create_username(personal=None, family=None)  # type: ignore
        self.assertEqual(username, "_")


class TestPaginatorSections(TestBase):
    def make_paginator(self, num_pages: int, page_index: int) -> Paginator[None]:
        # there's no need to initialize with real values
        p = Paginator[None](object_list=None, per_page=1)  # type: ignore[arg-type]
        p.num_pages = num_pages
        p._page_number = page_index
        return p

    def test_shortest(self) -> None:
        """Ensure paginator works correctly for only one page."""
        paginator = self.make_paginator(num_pages=1, page_index=1)
        sections = paginator.paginate_sections()
        self.assertEqual(list(sections), [1])

    def test_very_long(self) -> None:
        """Ensure paginator works correctly for big number of pages."""
        paginator = self.make_paginator(num_pages=20, page_index=1)
        sections = paginator.paginate_sections()
        self.assertEqual(
            list(sections),
            [1, 2, 3, 4, 5, None, 16, 17, 18, 19, 20],  # None is a break, '...'
        )

    def test_in_the_middle(self) -> None:
        """Ensure paginator puts two breaks when page index is in the middle
        of pages range."""
        paginator = self.make_paginator(num_pages=20, page_index=10)
        sections = paginator.paginate_sections()
        self.assertEqual(
            list(sections),
            # None is a break, it appears as '...' in the paginator widget
            [1, 2, 3, 4, 5, None, 8, 9, 10, 11, 12, 13, 14, None, 16, 17, 18, 19, 20],
        )

    def test_at_the_end(self) -> None:
        """Ensure paginator puts one break when page index is in the right-most
        part of pages range."""
        paginator = self.make_paginator(num_pages=20, page_index=20)
        sections = paginator.paginate_sections()
        self.assertEqual(
            list(sections),
            # None is a break, it appears as '...' in the paginator widget
            [1, 2, 3, 4, 5, None, 16, 17, 18, 19, 20],
        )

    def test_long_no_breaks(self) -> None:
        """Ensure paginator doesn't add breaks when sections touch each
        other."""
        paginator = self.make_paginator(num_pages=17, page_index=8)
        sections = paginator.paginate_sections()
        self.assertEqual(
            list(sections),
            # None is a break, it appears as '...' in the paginator widget
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
        )


class TestAssignUtil(TestBase):
    def setUp(self) -> None:
        """Set up RequestFactory for making fast fake requests."""
        self.person = Person.objects.create_user(
            username="test_user", email="user@test", personal="User", family="Test"
        )
        self.factory = RequestFactory()
        self.event = Event.objects.create(
            slug="event-for-assignment",
            host=Organization.objects.all()[0],
            assigned_to=None,
        )

    def test_assigning(self) -> None:
        """Ensure that with assignment is set correctly."""
        # Act
        assign(self.event, person=self.person)
        # Assert
        self.event.refresh_from_db()
        self.assertEqual(self.event.assigned_to, self.person)

    def test_removing_assignment(self) -> None:
        """Ensure that with person_id=None, the assignment is removed."""
        # Arrange
        self.event.assigned_to = self.person
        self.event.save()
        # Act
        assign(self.event, person=None)
        # Assert
        self.event.refresh_from_db()
        self.assertEqual(self.event.assigned_to, None)


class TestHumanDaterange(TestBase):
    def setUp(self) -> None:
        self.formats = {
            "no_date_left": "????",
            "no_date_right": "!!!!",
            "separator": " - ",
        }
        self.inputs = (
            (datetime(2018, 9, 1), datetime(2018, 9, 30)),
            (datetime(2018, 9, 30), datetime(2018, 9, 1)),
            (datetime(2018, 9, 1), datetime(2018, 12, 1)),
            (datetime(2018, 9, 1), datetime(2019, 12, 1)),
            (datetime(2018, 9, 1), None),
            (None, datetime(2018, 9, 1)),
            (None, None),
        )
        self.expected_outputs = (
            "Sep 01 - 30, 2018",
            "Sep 30 - 01, 2018",
            "Sep 01 - Dec 01, 2018",
            "Sep 01, 2018 - Dec 01, 2019",
            "Sep 01, 2018 - !!!!",
            "???? - Sep 01, 2018",
            "???? - !!!!",
        )

    def test_function(self) -> None:
        for i, v in enumerate(self.inputs):
            with self.subTest(i=i):
                left, right = v
                output = human_daterange(left, right, **self.formats)
                self.assertEqual(output, self.expected_outputs[i])


class TestMatchingNotificationEmail(TestBase):
    def setUp(self) -> None:
        self.request = WorkshopRequest.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="h@potter.com",
            institution_other_name="Hogwarts",
            institution_other_URL="hogwarts.uk",
            location="Scotland",
            country="GB",
            preferred_dates=None,
            other_preferred_dates="soon",
            language=Language.objects.get(name="English"),
            audience_description="Students of Hogwarts",
            administrative_fee="waiver",
            travel_expences_management="booked",
            institution_restrictions="no_restrictions",
        )

    def test_default_criteria(self) -> None:
        # Online
        self.request.country = "W3"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["workshops@carpentries.org"])

        # European Union
        self.request.country = "EU"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["workshops@carpentries.org"])

        # United States
        self.request.country = "US"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["workshops@carpentries.org"])

        # Poland
        self.request.country = "PL"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["workshops@carpentries.org"])

        # unknown country code
        self.request.country = "XY"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["workshops@carpentries.org"])

    def test_matching_Africa(self) -> None:
        """Testing just a subset of countries in Africa."""

        # the Democratic Republic of the Congo
        self.request.country = "CD"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["admin-afr@carpentries.org"])

        # Nigeria
        self.request.country = "NG"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["admin-afr@carpentries.org"])

        # South Sudan
        self.request.country = "SS"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["admin-afr@carpentries.org"])

        # Somalia
        self.request.country = "SO"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["admin-afr@carpentries.org"])

        # Egipt
        self.request.country = "EG"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["admin-afr@carpentries.org"])

        # Tunisia
        self.request.country = "TN"
        results = list(match_notification_email(self.request))
        self.assertEqual(results, ["admin-afr@carpentries.org"])

    def test_matching_UK_CA_NZ_AU(self) -> None:
        """Test a bunch of criteria automatically."""
        data = [
            ("GB", "admin-uk@carpentries.org"),
            ("CA", "admin-ca@carpentries.org"),
            ("NZ", "admin-nz@carpentries.org"),
            ("AU", "admin-au@carpentries.org"),
        ]
        for code, email in data:
            with self.subTest(code=code):
                self.request.country = code
                results = list(match_notification_email(self.request))
                self.assertEqual(results, [email])

    def test_object_no_criteria(self) -> None:
        self.assertFalse(hasattr(self, "country"))
        results = match_notification_email(self)
        self.assertEqual(results, ["workshops@carpentries.org"])

        self.country = None
        results = match_notification_email(self)
        self.assertEqual(results, ["workshops@carpentries.org"])


class TestReportsLink(TestBase):
    def setUp(self) -> None:
        self.slug = "2020-04-12-Krakow"

    def test_hash_lowercased_nonlowercased(self) -> None:
        self.assertEqual(reports_link_hash(self.slug), reports_link_hash(self.slug.lower()))

    def test_salts_alter_hash(self) -> None:
        hash_pre = reports_link_hash(self.slug)

        with self.settings(REPORTS_SALT_FRONT="test12345"):
            hash_salt_front = reports_link_hash(self.slug)

        with self.settings(REPORTS_SALT_BACK="test12345"):
            hash_salt_back = reports_link_hash(self.slug)

        with self.settings(REPORTS_SALT_FRONT="test12345", REPORTS_SALT_BACK="test12345"):
            hash_both_salts = reports_link_hash(self.slug)

        self.assertNotEqual(hash_pre, hash_salt_front)
        self.assertNotEqual(hash_pre, hash_salt_back)
        self.assertNotEqual(hash_pre, hash_both_salts)

        self.assertNotEqual(hash_salt_front, hash_both_salts)
        self.assertNotEqual(hash_salt_front, hash_salt_back)
        self.assertNotEqual(hash_salt_back, hash_both_salts)

    def test_link(self) -> None:
        """Ensure the link gets correctly generated."""

        with self.settings(REPORTS_LINK=""):
            link = reports_link(self.slug)
            self.assertEqual(link, "")

        with self.settings(REPORTS_LINK="{slug}"):
            link = reports_link(self.slug)
            self.assertEqual(link, self.slug)

        with self.settings(REPORTS_LINK="{slug}.{hash}"):
            link = reports_link(self.slug)
            parts = link.split(".")
            self.assertEqual(parts[0], self.slug)
            self.assertEqual(parts[1], reports_link_hash(self.slug))


class TestArchiveLeastRecentActiveConsents(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self.person_a = Person.objects.create(
            personal="A",
            family="Person",
            username="testing-A",
        )
        self.person_b = Person.objects.create(
            personal="B",
            family="Person",
            username="testing-B",
        )
        self.time_in_past = timezone.now() - timedelta(days=1)
        self.term_slugs = [term.slug for term in Term.objects.active()]
        self.base_obj = self.person_a

    def test_archive_least_recent_active_consents(self) -> None:
        """
        Archive the least recent consents that are
        currently active for the people given.
        """
        Consent.objects.filter(person=self.person_a).active().update(created_at=self.time_in_past)
        expected_consents = Consent.objects.filter(person=self.person_b).active()
        archive_least_recent_active_consents(self.person_a, self.person_b, self.base_obj)
        consents = Consent.objects.filter(person__in=[self.person_a, self.person_b]).active().select_related("term")
        # Assert we have all the consents we were expecting.
        self.assertCountEqual(self.term_slugs, [c.term.slug for c in consents])
        self.assertCountEqual(consents, expected_consents)

    def test_archive_least_recent_active_consents_equal_create(self) -> None:
        """
        When the created_at timestamp from both people are equal,
        archive both Consents and create a new one with term_option set to none
        and person set to base_object
        """
        Consent.objects.filter(person__in=[self.person_a, self.person_b]).active().update(created_at=self.time_in_past)
        archive_least_recent_active_consents(self.person_a, self.person_b, self.base_obj)
        consents = Consent.objects.filter(person__in=[self.person_a, self.person_b]).active()
        # Assert we have all the consents we were expecting.
        self.assertCountEqual(self.term_slugs, [c.term.slug for c in consents])
        for consent in consents:
            self.assertIsNone(consent.term_option)
            self.assertEqual(consent.person, self.base_obj)


class TestFeatureFlagEnabled(TestCase):
    def test_feature_flag_enabled_decorator(self) -> None:
        with (
            self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}),
            patch("src.workshops.utils.feature_flags.logger") as mock_logger,
        ):
            request = RequestFactory().get("/")

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs: Any) -> bool:
                return True

            self.assertEqual(test_func(request=request), None)
            mock_logger.debug.assert_called_once_with("EMAIL_MODULE feature flag not set, skipping test_func")

        with (
            self.settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]}),
            patch("src.workshops.utils.feature_flags.logger") as mock_logger,
        ):
            request = RequestFactory().get("/")

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs: Any) -> bool:
                return True

            self.assertEqual(test_func(request=request), True)
            mock_logger.debug.assert_not_called()

    def test_feature_flag_enabled_decorator__missing_request(self) -> None:
        DEBUG_MSG = "Cannot check EMAIL_MODULE feature flag, `request` parameter to test_func is missing"
        with (
            self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}),
            patch("src.workshops.utils.feature_flags.logger") as mock_logger,
        ):

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs: Any) -> bool:
                return True

            self.assertEqual(test_func(), None)
            mock_logger.debug.assert_called_once_with(DEBUG_MSG)

        with (
            self.settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]}),
            patch("src.workshops.utils.feature_flags.logger") as mock_logger,
        ):

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs: Any) -> bool:
                return True

            self.assertEqual(test_func(), None)
            mock_logger.debug.assert_called_once_with(DEBUG_MSG)


class TestSafeNextOrDefaultURL(TestCase):
    def test_default_url_if_next_empty(self) -> None:
        # Arrange
        next_url = None
        default_url = "/dashboard/"
        # Act
        url = safe_next_or_default_url(next_url, default_url)
        # Assert
        self.assertEqual(url, default_url)

    def test_default_url_if_next_not_provided(self) -> None:
        # Arrange
        next_url = ""
        default_url = "/dashboard/"
        # Act
        url = safe_next_or_default_url(next_url, default_url)
        # Assert
        self.assertEqual(url, default_url)

    def test_default_url_if_next_not_safe(self) -> None:
        # Arrange
        next_url = "https://google.com"
        default_url = "/dashboard/"
        # Act
        url = safe_next_or_default_url(next_url, default_url)
        # Assert
        self.assertEqual(url, default_url)

    def test_next_url_if_next_safe(self) -> None:
        # Arrange
        next_url = "/admin/"
        default_url = "/dashboard/"
        # Act
        url = safe_next_or_default_url(next_url, default_url)
        # Assert
        self.assertEqual(url, next_url)

    def test_when_default_is_not_safe(self) -> None:
        # Arrange
        next_url = ""
        default_url = "https://malicious.com"
        # Act
        url = safe_next_or_default_url(next_url, default_url)
        # Assert
        self.assertEqual(url, "/")  # Safe fallback
