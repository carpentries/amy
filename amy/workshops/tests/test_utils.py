from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone
import requests.exceptions
import requests_mock

from consents.models import Consent, Term
from workshops.exceptions import InternalError
from workshops.models import Event, Language, Organization, Person, WorkshopRequest
from workshops.tests.base import TestBase
from workshops.utils.consents import archive_least_recent_active_consents
from workshops.utils.dates import human_daterange
from workshops.utils.emails import match_notification_email
from workshops.utils.feature_flags import feature_flag_enabled
from workshops.utils.metadata import (
    datetime_decode,
    datetime_match,
    fetch_workshop_metadata,
    find_workshop_HTML_metadata,
    find_workshop_YAML_metadata,
    generate_url_to_event_index,
    metadata_deserialize,
    metadata_serialize,
    parse_workshop_metadata,
    validate_workshop_metadata,
)
from workshops.utils.pagination import Paginator
from workshops.utils.reports import reports_link, reports_link_hash
from workshops.utils.usernames import create_username
from workshops.utils.views import assign


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

    @requests_mock.Mocker()
    def test_fetching_event_metadata_html(self, mock):
        "Ensure 'fetch_workshop_metadata' works correctly with HTML metadata provided."
        website_url = "https://pbanaszkiewicz.github.io/workshop"
        repo_url = (
            "https://raw.githubusercontent.com/pbanaszkiewicz/"
            "workshop/gh-pages/index.html"
        )
        mock.get(website_url, text=self.html_content, status_code=200)
        mock.get(repo_url, text="", status_code=200)
        metadata = fetch_workshop_metadata(website_url)
        self.assertEqual(metadata["slug"], "2015-07-13-test")

    @requests_mock.Mocker()
    def test_fetching_event_metadata_yaml(self, mock):
        "Ensure 'fetch_workshop_metadata' works correctly with YAML metadata provided."
        website_url = "https://pbanaszkiewicz.github.io/workshop"
        repo_url = (
            "https://raw.githubusercontent.com/pbanaszkiewicz/"
            "workshop/gh-pages/index.html"
        )
        mock.get(website_url, text="", status_code=200)
        mock.get(repo_url, text=self.yaml_content, status_code=200)
        metadata = fetch_workshop_metadata(website_url)
        self.assertEqual(metadata["slug"], "workshop")

    @requests_mock.Mocker()
    def test_fetching_event_metadata_timeout(self, mock):
        "Ensure 'fetch_workshop_metadata' reacts to timeout."
        website_url = "https://pbanaszkiewicz.github.io/workshop"
        mock.register_uri(
            "GET",
            website_url,
            exc=requests.exceptions.ConnectTimeout,
        )
        with self.assertRaises(requests.exceptions.ConnectTimeout):
            fetch_workshop_metadata(website_url)

    def test_generating_url_to_index(self):
        tests = [
            "http://swcarpentry.github.io/workshop-template",
            "https://swcarpentry.github.com/workshop-template",
            "http://swcarpentry.github.com/workshop-template/",
            "http://github.com/swcarpentry/workshop-template",
            "https://github.com/swcarpentry/workshop-template",
        ]
        expected_url = (
            "https://raw.githubusercontent.com/swcarpentry/"
            "workshop-template/gh-pages/index.html"
        )
        expected_repo = "workshop-template"
        for url in tests:
            with self.subTest(url=url):
                url, repo = generate_url_to_event_index(url)
                self.assertEqual(expected_url, url)
                self.assertEqual(expected_repo, repo)

    def test_finding_metadata_on_index(self):
        content = self.yaml_content
        expected = {
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "latlng": "36.998977, -109.045173",
            "language": "us",
            "instructor": "Hermione Granger|Ron Weasley",
            "helper": "Peter Parker|Tony Stark|Natasha Romanova",
            "contact": "hermione@granger.co.uk|rweasley@ministry.gov",
            "eventbrite": "10000000",
        }
        self.assertEqual(expected, find_workshop_YAML_metadata(content))

    def test_finding_metadata_on_website(self):
        content = self.html_content
        expected = {
            "slug": "2015-07-13-test",
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "latlng": "36.998977, -109.045173",
            "language": "us",
            "instructor": "Hermione Granger|Ron Weasley",
            "helper": "Peter Parker|Tony Stark|Natasha Romanova",
            "contact": "hermione@granger.co.uk|rweasley@ministry.gov",
            "eventbrite": "10000000",
        }

        self.assertEqual(expected, find_workshop_HTML_metadata(content))

    def test_finding_metadata_empty_tags(self):
        content = """
            <html><head>
            <meta name="slug" content="" />
            <meta name="startdate" content="" />
            <meta name="enddate" content="" />
            <meta name="country" content="" />
            <meta name="venue" content="" />
            <meta name="address" content="" />
            <meta name="latlng" content="" />
            <meta name="language" content="" />
            <meta name="invalid" content="" />
            <meta name="instructor" content="" />
            <meta name="helper" content="" />
            <meta name="contact" content="" />
            <meta name="eventbrite" content="" />
            <meta name="charset" content="" />
            </head>
            <body>
            <h1>test</h1>
            </body></html>
        """
        expected = {
            "slug": "",
            "startdate": "",
            "enddate": "",
            "country": "",
            "venue": "",
            "address": "",
            "latlng": "",
            "language": "",
            "instructor": "",
            "helper": "",
            "contact": "",
            "eventbrite": "",
        }
        self.assertEqual(expected, find_workshop_HTML_metadata(content))

    def test_finding_metadata_missing_tags(self):
        content = """
            <html><head>
            <meta name="slug" content="" />
            <meta name="charset" content="utf-8" />
            </head>
            <body>
            <h1>test</h1>
            </body></html>
        """
        expected = {
            "slug": "",
        }
        self.assertEqual(expected, find_workshop_HTML_metadata(content))

    def test_finding_metadata_single_line(self):
        content = (
            "<html><head>"
            '<meta name="slug" content="" />'
            '<meta name="charset" content="utf-8" />'
            "</head>"
            "<body>"
            "<h1>test</h1>"
            "</body></html>"
        )
        expected = {
            "slug": "",
        }
        self.assertEqual(expected, find_workshop_HTML_metadata(content))

    def test_finding_metadata_empty_page(self):
        content1 = "<html><head></head><body></body></html>"
        content2 = ""
        expected = {}
        self.assertEqual(expected, find_workshop_HTML_metadata(content1))
        self.assertEqual(expected, find_workshop_HTML_metadata(content2))

    def test_parsing_empty_metadata(self):
        empty_dict = {}
        expected = {
            "slug": "",
            "language": "",
            "start": None,
            "end": None,
            "country": "",
            "venue": "",
            "address": "",
            "latitude": None,
            "longitude": None,
            "reg_key": None,
            "instructors": [],
            "helpers": [],
            "contact": [],
        }
        self.assertEqual(expected, parse_workshop_metadata(empty_dict))

    def test_parsing_correct_metadata(self):
        metadata = {
            "slug": "2015-07-13-test",
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "latlng": "36.998977, -109.045173",
            "language": "us",
            "instructor": "Hermione Granger|Ron Weasley",
            "helper": "Peter Parker|Tony Stark|Natasha Romanova",
            "contact": "hermione@granger.co.uk|rweasley@ministry.gov",
            "eventbrite": "10000000",
        }
        expected = {
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
        self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_parsing_tricky_country_language(self):
        """Ensure we always get a 2-char string or nothing."""
        tests = [
            (("Usa", "English"), ("US", "EN")),
            (("U", "E"), ("", "")),
            (("", ""), ("", "")),
        ]
        expected = {
            "slug": "",
            "language": "",
            "start": None,
            "end": None,
            "country": "",
            "venue": "",
            "address": "",
            "latitude": None,
            "longitude": None,
            "reg_key": None,
            "instructors": [],
            "helpers": [],
            "contact": [],
        }

        for (country, language), (country_exp, language_exp) in tests:
            with self.subTest(iso_31661=(country, language)):
                metadata = dict(country=country, language=language)
                expected["country"] = country_exp
                expected["language"] = language_exp
                self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_parsing_tricky_dates(self):
        """Test if non-dates don't get parsed."""
        tests = [
            (("wrong start date", "wrong end date"), (None, None)),
            (("11/19/2015", "11/19/2015"), (None, None)),
        ]
        expected = {
            "slug": "",
            "language": "",
            "start": None,
            "end": None,
            "country": "",
            "venue": "",
            "address": "",
            "latitude": None,
            "longitude": None,
            "reg_key": None,
            "instructors": [],
            "helpers": [],
            "contact": [],
        }

        for (startdate, enddate), (start, end) in tests:
            with self.subTest(dates=(startdate, enddate)):
                metadata = dict(startdate=startdate, enddate=enddate)
                expected["start"] = start
                expected["end"] = end
                self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_parsing_tricky_list_of_names(self):
        """Ensure we always get a list."""
        tests = [
            (("", ""), ([], [])),
            (
                ("Hermione Granger", "Peter Parker"),
                (["Hermione Granger"], ["Peter Parker"]),
            ),
            (("Harry,Ron", "Hermione,Ginny"), (["Harry,Ron"], ["Hermione,Ginny"])),
            (
                ("Harry| Ron", "Hermione |Ginny"),
                (["Harry", "Ron"], ["Hermione", "Ginny"]),
            ),
        ]
        expected = {
            "slug": "",
            "language": "",
            "start": None,
            "end": None,
            "country": "",
            "venue": "",
            "address": "",
            "latitude": None,
            "longitude": None,
            "reg_key": None,
            "instructors": [],
            "helpers": [],
            "contact": [],
        }

        for (instructor, helper), (instructors, helpers) in tests:
            with self.subTest(people=(instructor, helper)):
                metadata = dict(instructor=instructor, helper=helper)
                expected["instructors"] = instructors
                expected["helpers"] = helpers
                self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_parsing_tricky_latitude_longitude(self):
        tests = [
            ("XYZ", (None, None)),
            ("XYZ, ", (None, None)),
            (",-123", (None, -123.0)),
            (",", (None, None)),
            (None, (None, None)),
        ]
        expected = {
            "slug": "",
            "language": "",
            "start": None,
            "end": None,
            "country": "",
            "venue": "",
            "address": "",
            "latitude": None,
            "longitude": None,
            "reg_key": None,
            "instructors": [],
            "helpers": [],
            "contact": [],
        }
        for latlng, (latitude, longitude) in tests:
            with self.subTest(latlng=latlng):
                metadata = dict(latlng=latlng)
                expected["latitude"] = latitude
                expected["longitude"] = longitude
                self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_parsing_tricky_eventbrite_id(self):
        tests = [
            ("", None),
            ("string", None),
            (None, None),
        ]
        expected = {
            "slug": "",
            "language": "",
            "start": None,
            "end": None,
            "country": "",
            "venue": "",
            "address": "",
            "latitude": None,
            "longitude": None,
            "reg_key": None,
            "instructors": [],
            "helpers": [],
            "contact": [],
        }
        for eventbrite_id, reg_key in tests:
            with self.subTest(eventbrite_id=eventbrite_id):
                metadata = dict(eventbrite=eventbrite_id)
                expected["reg_key"] = reg_key
                self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_validating_invalid_metadata(self):
        metadata = {
            "slug": "WRONG FORMAT",
            "language": "ENGLISH",
            "startdate": "07/13/2015",
            "enddate": "07/14/2015",
            "country": "USA",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "latlng": "3699e-4, -1.09e2",
            "instructor": "Hermione Granger, Ron Weasley",
            "helper": "Peter Parker, Tony Stark, Natasha Romanova",
            "contact": "hermione@granger.co.uk, rweasley@ministry.gov",
            "eventbrite": "bigmoney",
        }
        errors, warnings = validate_workshop_metadata(metadata)
        assert len(errors) == 7
        assert not warnings
        assert all([error.startswith("Invalid value") for error in errors])

    def test_validating_missing_metadata(self):
        metadata = {}
        errors, warnings = validate_workshop_metadata(metadata)
        assert len(errors) == 9  # There are nine required fields
        assert len(warnings) == 3  # There are three optional fields
        assert all([issue.startswith("Missing") for issue in (errors + warnings)])

    def test_validating_empty_metadata(self):
        metadata = {
            "slug": "",
            "language": "",
            "startdate": "",
            "enddate": "",
            "country": "",
            "venue": "",
            "address": "",
            "latlng": "",
            "instructor": "",
            "helper": "",
            "contact": "",
            "eventbrite": "",
        }
        expected_errors = [
            "slug",
            "startdate",
            "country",
            "latlng",
            "instructor",
            "helper",
            "contact",
        ]
        errors, warnings = validate_workshop_metadata(metadata)
        assert not warnings
        for error, key in zip(errors, expected_errors):
            self.assertIn(key, error)

    def test_validating_default_metadata(self):
        metadata = {
            "slug": "FIXME",
            "language": "FIXME",
            "startdate": "FIXME",
            "enddate": "FIXME",
            "country": "FIXME",
            "venue": "FIXME",
            "address": "FIXME",
            "latlng": "FIXME",
            "eventbrite": "FIXME",
            "instructor": "FIXME",
            "helper": "FIXME",
            "contact": "FIXME",
        }
        errors, warnings = validate_workshop_metadata(metadata)
        assert len(errors) == 12
        assert not warnings
        assert all([error.startswith('Placeholder value "FIXME"') for error in errors])

    def test_validating_correct_metadata(self):
        metadata = {
            "slug": "2015-07-13-test",
            "language": "us",
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "latlng": "36.998977, -109.045173",
            "eventbrite": "10000000",
            "instructor": "Hermione Granger, Ron Weasley",
            "helper": "Peter Parker, Tony Stark, Natasha Romanova",
            "contact": "hermione@granger.co.uk, rweasley@ministry.gov",
        }
        errors, warnings = validate_workshop_metadata(metadata)
        assert not warnings
        assert not errors

    def test_no_attribute_error_missing_instructors_helpers(self):
        """Regression test: ensure no exception is raised when instructors
        or helpers aren't in the metadata or their values are None."""
        tests = [
            ((None, None), ([], [])),
            ((None, ""), ([], [])),
            (("", None), ([], [])),
        ]
        expected = {
            "slug": "",
            "language": "",
            "start": None,
            "end": None,
            "country": "",
            "venue": "",
            "address": "",
            "latitude": None,
            "longitude": None,
            "reg_key": None,
            "instructors": [],
            "helpers": [],
            "contact": [],
        }

        for (instructor, helper), (instructors, helpers) in tests:
            with self.subTest(people=(instructor, helper)):
                metadata = dict(instructor=instructor, helper=helper)
                expected["instructors"] = instructors
                expected["helpers"] = helpers
                self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_metadata_serialization(self) -> None:
        # Act
        serialized_json = metadata_serialize(self.expected_metadata_parsed)
        # Assert
        self.assertIn("2015-07-13", serialized_json)
        self.assertIn("2015-07-14", serialized_json)
        self.assertIn("2015-07-13-test", serialized_json)
        self.assertIn("-109.045173", serialized_json)
        self.assertIn("36.998977", serialized_json)
        self.assertIn(
            '["hermione@granger.co.uk", "rweasley@ministry.gov"]', serialized_json
        )

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


class TestAlternativeLatitudeLongitude(TestBase):
    maxDiff = None

    html_content_old = """
<html><head>
<meta name="latlng" content="36.998977, -109.045173" />
</head>
<body>
<h1>test</h1>
</body></html>
"""
    html_content_new = """
<html><head>
<meta name="lat" content="36.998977" />
<meta name="lng" content="-109.045173" />
</head>
<body>
<h1>test</h1>
</body></html>
"""
    yaml_content_old = """---
layout: workshop
root: .
latlng: 36.998977, -109.045173
----
Other content.
"""
    yaml_content_new = """---
layout: workshop
root: .
lat: 36.998977
lng: -109.045173
----
Other content.
"""

    def test_finding_metadata_on_index(self):
        content = self.yaml_content_old
        expected = {
            "latlng": "36.998977, -109.045173",
        }
        self.assertEqual(expected, find_workshop_YAML_metadata(content))

        content = self.yaml_content_new
        expected = {
            "lat": "36.998977",
            "lng": "-109.045173",
        }
        self.assertEqual(expected, find_workshop_YAML_metadata(content))

    def test_finding_metadata_on_website(self):
        content = self.html_content_old
        expected = {
            "latlng": "36.998977, -109.045173",
        }
        self.assertEqual(expected, find_workshop_HTML_metadata(content))

        content = self.html_content_new
        expected = {
            "lat": "36.998977",
            "lng": "-109.045173",
        }
        self.assertEqual(expected, find_workshop_HTML_metadata(content))

    def test_parsing_old_latlng(self):
        metadata = {
            "slug": "2015-07-13-test",
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "latlng": "36.998977, -109.045173",
            "language": "us",
            "instructor": "Hermione Granger|Ron Weasley",
            "helper": "Peter Parker|Tony Stark|Natasha Romanova",
            "contact": "hermione@granger.co.uk|rweasley@ministry.gov",
            "eventbrite": "10000000",
        }
        expected = {
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
        self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_parsing_new_latlng(self):
        metadata = {
            "slug": "2015-07-13-test",
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "lat": "36.998977",
            "lng": "-109.045173",
            "language": "us",
            "instructor": "Hermione Granger|Ron Weasley",
            "helper": "Peter Parker|Tony Stark|Natasha Romanova",
            "contact": "hermione@granger.co.uk|rweasley@ministry.gov",
            "eventbrite": "10000000",
        }
        expected = {
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
        self.assertEqual(expected, parse_workshop_metadata(metadata))

    def test_validating_old_latlng(self):
        """"""
        metadata = {
            "slug": "2015-07-13-test",
            "language": "us",
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "eventbrite": "10000000",
            "instructor": "Hermione Granger, Ron Weasley",
            "helper": "Peter Parker, Tony Stark, Natasha Romanova",
            "contact": "hermione@granger.co.uk, rweasley@ministry.gov",
            "latlng": "36.998977, -109.045173",
        }
        errors, warnings = validate_workshop_metadata(metadata)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_validating_new_latlng(self):
        """"""
        metadata = {
            "slug": "2015-07-13-test",
            "language": "us",
            "startdate": "2015-07-13",
            "enddate": "2015-07-14",
            "country": "us",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "eventbrite": "10000000",
            "instructor": "Hermione Granger, Ron Weasley",
            "helper": "Peter Parker, Tony Stark, Natasha Romanova",
            "contact": "hermione@granger.co.uk, rweasley@ministry.gov",
            "lat": "36.998977",
            "lng": "-109.045173",
        }
        errors, warnings = validate_workshop_metadata(metadata)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


class TestUsernameGeneration(TestBase):
    def setUp(self):
        Person.objects.create_user(
            username="potter_harry",
            personal="Harry",
            family="Potter",
            email="hp@ministry.gov",
        )

    def test_conflicting_name(self):
        """Ensure `create_username` works correctly when conflicting username
        already exists."""
        username = create_username(personal="Harry", family="Potter")
        self.assertEqual(username, "potter_harry_2")

    def test_nonconflicting_name(self):
        """Ensure `create_username` works correctly when there's no conflicts
        in the database."""
        username = create_username(personal="Hermione", family="Granger")
        self.assertEqual(username, "granger_hermione")

    def test_nonlatin_characters(self):
        """Ensure correct behavior for non-latin names."""
        username = create_username(personal="Grzegorz", family="Brzęczyszczykiewicz")
        self.assertEqual(username, "brzczyszczykiewicz_grzegorz")

    def test_reached_number_of_tries(self):
        """Ensure we don't DoS ourselves."""
        tries = 1
        with self.assertRaises(InternalError):
            create_username(personal="Harry", family="Potter", tries=tries)

    def test_hyphenated_name(self):
        """Ensure people with hyphens in names have correct usernames
        generated."""
        username = create_username(personal="Andy", family="Blanking-Crush")
        self.assertEqual(username, "blanking-crush_andy")

    def test_noned_names(self):
        """This is a regression test against #1682
        (https://github.com/carpentries/amy/issues/1682).

        The error was: family name was allowed to be null, which caused 500 errors
        when trying to save person without the family name due to name normalization."""
        username = create_username(personal=None, family=None)
        self.assertEqual(username, "_")


class TestPaginatorSections(TestBase):
    def make_paginator(self, num_pages, page_index=None):
        # there's no need to initialize with real values
        p = Paginator(object_list=None, per_page=1)
        p.num_pages = num_pages
        p._page_number = page_index
        return p

    def test_shortest(self):
        """Ensure paginator works correctly for only one page."""
        paginator = self.make_paginator(num_pages=1, page_index=1)
        sections = paginator.paginate_sections()
        self.assertEqual(list(sections), [1])

    def test_very_long(self):
        """Ensure paginator works correctly for big number of pages."""
        paginator = self.make_paginator(num_pages=20, page_index=1)
        sections = paginator.paginate_sections()
        self.assertEqual(
            list(sections),
            [1, 2, 3, 4, 5, None, 16, 17, 18, 19, 20],  # None is a break, '...'
        )

    def test_in_the_middle(self):
        """Ensure paginator puts two breaks when page index is in the middle
        of pages range."""
        paginator = self.make_paginator(num_pages=20, page_index=10)
        sections = paginator.paginate_sections()
        self.assertEqual(
            list(sections),
            # None is a break, it appears as '...' in the paginator widget
            [1, 2, 3, 4, 5, None, 8, 9, 10, 11, 12, 13, 14, None, 16, 17, 18, 19, 20],
        )

    def test_at_the_end(self):
        """Ensure paginator puts one break when page index is in the right-most
        part of pages range."""
        paginator = self.make_paginator(num_pages=20, page_index=20)
        sections = paginator.paginate_sections()
        self.assertEqual(
            list(sections),
            # None is a break, it appears as '...' in the paginator widget
            [1, 2, 3, 4, 5, None, 16, 17, 18, 19, 20],
        )

    def test_long_no_breaks(self):
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
    def setUp(self):
        """Set up RequestFactory for making fast fake requests."""
        self.person = Person.objects.create_user(  # type: ignore
            username="test_user", email="user@test", personal="User", family="Test"
        )
        self.factory = RequestFactory()
        self.event = Event.objects.create(
            slug="event-for-assignment",
            host=Organization.objects.first(),
            assigned_to=None,
        )

    def test_assigning(self):
        """Ensure that with assignment is set correctly."""
        # Act
        assign(self.event, person=self.person)
        # Assert
        self.event.refresh_from_db()
        self.assertEqual(self.event.assigned_to, self.person)

    def test_removing_assignment(self):
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
    def setUp(self):
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

    def test_function(self):
        for i, v in enumerate(self.inputs):
            with self.subTest(i=i):
                left, right = v
                output = human_daterange(left, right, **self.formats)
                self.assertEqual(output, self.expected_outputs[i])


class TestMatchingNotificationEmail(TestBase):
    def setUp(self):
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

    def test_default_criteria(self):
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

    def test_matching_Africa(self):
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

    def test_matching_UK_CA_NZ_AU(self):
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

    def test_object_no_criteria(self):
        self.assertFalse(hasattr(self, "country"))
        results = match_notification_email(self)
        self.assertEqual(results, ["workshops@carpentries.org"])

        self.country = None
        results = match_notification_email(self)
        self.assertEqual(results, ["workshops@carpentries.org"])


class TestReportsLink(TestBase):
    def setUp(self):
        self.slug = "2020-04-12-Krakow"

    def test_hash_lowercased_nonlowercased(self):
        self.assertEqual(
            reports_link_hash(self.slug), reports_link_hash(self.slug.lower())
        )

    def test_salts_alter_hash(self):
        hash_pre = reports_link_hash(self.slug)

        with self.settings(REPORTS_SALT_FRONT="test12345"):
            hash_salt_front = reports_link_hash(self.slug)

        with self.settings(REPORTS_SALT_BACK="test12345"):
            hash_salt_back = reports_link_hash(self.slug)

        with self.settings(
            REPORTS_SALT_FRONT="test12345", REPORTS_SALT_BACK="test12345"
        ):
            hash_both_salts = reports_link_hash(self.slug)

        self.assertNotEqual(hash_pre, hash_salt_front)
        self.assertNotEqual(hash_pre, hash_salt_back)
        self.assertNotEqual(hash_pre, hash_both_salts)

        self.assertNotEqual(hash_salt_front, hash_both_salts)
        self.assertNotEqual(hash_salt_front, hash_salt_back)
        self.assertNotEqual(hash_salt_back, hash_both_salts)

    def test_link(self):
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
    def setUp(self):
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
        Consent.objects.filter(person=self.person_a).active().update(
            created_at=self.time_in_past
        )
        expected_consents = Consent.objects.filter(person=self.person_b).active()
        archive_least_recent_active_consents(
            self.person_a, self.person_b, self.base_obj
        )
        consents = (
            Consent.objects.filter(person__in=[self.person_a, self.person_b])
            .active()
            .select_related("term")
        )
        # Assert we have all the consents we were expecting.
        self.assertCountEqual(self.term_slugs, [c.term.slug for c in consents])
        self.assertCountEqual(consents, expected_consents)

    def test_archive_least_recent_active_consents_equal_create(self) -> None:
        """
        When the created_at timestamp from both people are equal,
        archive both Consents and create a new one with term_option set to none
        and person set to base_object
        """
        Consent.objects.filter(
            person__in=[self.person_a, self.person_b]
        ).active().update(created_at=self.time_in_past)
        archive_least_recent_active_consents(
            self.person_a, self.person_b, self.base_obj
        )
        consents = Consent.objects.filter(
            person__in=[self.person_a, self.person_b]
        ).active()
        # Assert we have all the consents we were expecting.
        self.assertCountEqual(self.term_slugs, [c.term.slug for c in consents])
        for consent in consents:
            self.assertIsNone(consent.term_option)
            self.assertEqual(consent.person, self.base_obj)


class TestFeatureFlagEnabled(TestCase):
    def test_feature_flag_enabled_decorator(self) -> None:
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}), patch(
            "workshops.utils.feature_flags.logger"
        ) as mock_logger:
            request = RequestFactory().get("/")

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs):
                return True

            self.assertEqual(test_func(request=request), None)
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping test_func"
            )

        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]}), patch(
            "workshops.utils.feature_flags.logger"
        ) as mock_logger:
            request = RequestFactory().get("/")

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs):
                return True

            self.assertEqual(test_func(request=request), True)
            mock_logger.debug.assert_not_called()

    def test_feature_flag_enabled_decorator__missing_request(self) -> None:
        DEBUG_MSG = (
            "Cannot check EMAIL_MODULE feature flag, `request` parameter to "
            "test_func is missing"
        )
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}), patch(
            "workshops.utils.feature_flags.logger"
        ) as mock_logger:

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs):
                return True

            self.assertEqual(test_func(), None)
            mock_logger.debug.assert_called_once_with(DEBUG_MSG)

        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]}), patch(
            "workshops.utils.feature_flags.logger"
        ) as mock_logger:

            @feature_flag_enabled("EMAIL_MODULE")
            def test_func(**kwargs):
                return True

            self.assertEqual(test_func(), None)
            mock_logger.debug.assert_called_once_with(DEBUG_MSG)
