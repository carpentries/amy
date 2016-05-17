"""This file contains tests for individual management commands

These commands are run via `./manage.py command`."""

from datetime import date, datetime, time
import unittest
from unittest.mock import MagicMock

from django.core.management import call_command
from django.test import TestCase
import requests_mock

from .base import TestBase
from ..management.commands.fake_database import (
    Command as FakeDatabaseCommand,
    Faker
)
from ..management.commands.instructors_activity import (
    Command as InstructorsActivityCommand)
from ..management.commands.check_for_workshop_websites_updates import (
    Command as WebsiteUpdatesCommand,
    WrongWorkshopURL,
    datetime_match,
    datetime_decode)
from ..models import (
    Airport,
    Role,
    Badge,
    Tag,
    Person,
    Host,
    Event,
    Task,
)


class TestFakeDatabaseCommand(TestCase):
    def setUp(self):
        self.cmd = FakeDatabaseCommand()
        self.seed = 12345
        self.faker = Faker()
        self.faker.seed(self.seed)

    def test_no_airports_created(self):
        """Make sure we don't create any airports.

        We don't want to create them, because data migrations add some, and in
        the future we want to add them via fixture (see #626)."""
        airports_before = set(Airport.objects.all())
        self.cmd.fake_airports(self.faker)
        airports_after = set(Airport.objects.all())

        self.assertEqual(airports_before, airports_after)

    def test_new_roles_added(self):
        """Make sure we add roles that are hard-coded. They'll end up in
        fixtures in future (see #626)."""
        roles = ['helper', 'instructor', 'host', 'learner', 'organizer',
                 'tutor', 'debriefed']
        self.assertFalse(Role.objects.filter(name__in=roles).exists())
        self.cmd.fake_roles(self.faker)

        self.assertEqual(set(roles),
                         set(Role.objects.values_list('name', flat=True)))

    def test_new_tags_added(self):
        """Make sure we add tags that are hard-coded. They'll end up in
        fixtures in future (see #626)."""
        tags = ['SWC', 'DC', 'LC', 'WiSE', 'TTT', 'online', 'stalled',
                'unresponsive', 'hackathon']
        self.assertNotEqual(set(tags),
                            set(Tag.objects.values_list('name', flat=True)))

        self.cmd.fake_tags(self.faker)
        self.assertEqual(set(tags),
                         set(Tag.objects.values_list('name', flat=True)))

    def test_new_badges_added(self):
        """Make sure we add badges that are hard-coded. They'll end up in
        fixtures in future (see #626)."""
        badges_pre = [
            'swc-instructor', 'dc-instructor', 'maintainer', 'trainer',
        ]
        badges_post = ['creator', 'member', 'organizer']
        self.assertEqual(set(badges_pre),
                         set(Badge.objects.values_list('name', flat=True)))

        self.cmd.fake_badges(self.faker)
        self.assertEqual(set(badges_pre + badges_post),
                         set(Badge.objects.values_list('name', flat=True)))

    def test_database_populated(self):
        """Make sure the database is getting populated."""
        self.assertFalse(Person.objects.exists())
        self.assertFalse(Host.objects.exclude(domain='self-organized')
                                     .exists())
        self.assertFalse(Event.objects.exists())
        self.assertFalse(Task.objects.exists())

        call_command('fake_database', seed=self.seed)

        self.assertTrue(Person.objects.exists())
        self.assertTrue(Host.objects.exclude(domain='self-organized').exists())
        self.assertTrue(Event.objects.exists())
        self.assertTrue(Task.objects.exists())


class TestInstructorsActivityCommand(TestBase):
    def setUp(self):
        self.cmd = InstructorsActivityCommand()

        # add instructors
        self._setUpLessons()
        self._setUpBadges()
        self._setUpAirports()
        self._setUpInstructors()

        # and some non-instructors
        self._setUpNonInstructors()

        # add one event that some instructors took part in
        self._setUpHosts()
        self.event = Event.objects.create(
            slug='event-with-tasks',
            host=self.host_alpha,
            start=date(2015, 8, 30),
        )
        self._setUpRoles()
        self.instructor = Role.objects.get(name='instructor')
        self.helper = Role.objects.get(name='helper')
        self.learner = Role.objects.get(name='learner')

        Task.objects.bulk_create([
            Task(event=self.event, person=self.hermione, role=self.instructor),
            Task(event=self.event, person=self.ron, role=self.instructor),
            Task(event=self.event, person=self.ron, role=self.helper),
            Task(event=self.event, person=self.harry, role=self.helper),
            Task(event=self.event, person=self.spiderman, role=self.learner),
            Task(event=self.event, person=self.blackwidow, role=self.learner),
        ])

    def test_getting_foreign_tasks(self):
        """Make sure we get tasks for other people (per event)."""
        person = self.hermione
        roles = [self.instructor, self.helper]
        tasks = person.task_set.filter(role__in=roles)

        # index 0, because Hermione has only one task and we're checking it
        fg_tasks = self.cmd.foreign_tasks(tasks, person, roles)[0]

        # we should receive other instructors and helpers for self.event
        expecting = set([
            Task.objects.get(event=self.event, person=self.ron,
                             role=self.instructor),
            Task.objects.get(event=self.event, person=self.ron,
                             role=self.helper),
            Task.objects.get(event=self.event, person=self.harry,
                             role=self.helper),
        ])

        self.assertEqual(expecting, set(fg_tasks))

    def test_fetching_activity(self):
        """Make sure we get correct results for all instructors."""
        # include people who don't want to be contacted (other option is tested
        # in `self.test_fetching_activity_may_contact_only`)
        results = self.cmd.fetch_activity(may_contact_only=False)
        instructor_badges = Badge.objects.instructor_badges()

        persons = [d['person'] for d in results]
        lessons = [list(d['lessons']) for d in results]
        instructor_awards = [list(d['instructor_awards']) for d in results]
        tasks = [d['tasks'] for d in results]

        expecting_persons = [self.hermione, self.harry, self.ron]
        expecting_lessons = [list(self.hermione.lessons.all()),
                             list(self.harry.lessons.all()),
                             list(self.ron.lessons.all())]
        expecting_awards = [
            list(person.award_set.filter(badge__in=instructor_badges))
            for person in expecting_persons
        ]

        self.assertEqual(set(persons), set(expecting_persons))
        self.assertEqual(lessons, expecting_lessons)
        self.assertEqual(instructor_awards, expecting_awards)

        for task in tasks:
            for own_task, foreign_tasks in task:
                # we don't test foreign tasks, since they should be tested in
                # `self.test_getting_foreign_tasks`
                self.assertIn(
                    own_task,
                    own_task.person.task_set.filter(
                        role__name__in=['instructor', 'helper']
                    )
                )

    def test_fetching_activity_may_contact_only(self):
        """Make sure we get results only for people we can send emails to."""
        # let's make Harry willing to receive emails
        self.hermione.may_contact = False
        self.harry.may_contact = True
        self.ron.may_contact = False
        self.hermione.save()
        self.harry.save()
        self.ron.save()

        results = self.cmd.fetch_activity(may_contact_only=True)
        persons = [d['person'] for d in results]
        expecting_persons = [self.harry]
        self.assertEqual(set(persons), set(expecting_persons))


class TestWebsiteUpdatesCommand(TestBase):
    maxDiff = None

    def setUp(self):
        self.cmd = WebsiteUpdatesCommand()
        self.fake_cmd = FakeDatabaseCommand()
        self.seed = 12345
        self.faker = Faker()
        self.faker.seed(self.seed)

        self.fake_cmd.fake_hosts(self.faker)

        self.mocked_event_page = """
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
<meta name="contact" content="hermione@granger.co.uk, rweasley@ministry.gov" />
<meta name="eventbrite" content="10000000" />
<meta name="charset" content="utf-8" />
</head>
<body>
<h1>test</h1>
</body></html>
"""
        self.expected_metadata_parsed = {
            'slug': '2015-07-13-test',
            'language': 'US',
            'start': date(2015, 7, 13),
            'end': date(2015, 7, 14),
            'country': 'US',
            'venue': 'Euphoric State University',
            'address': 'Highway to Heaven 42, Academipolis',
            'latitude': 36.998977,
            'longitude': -109.045173,
            'reg_key': 10000000,
            'instructors': ['Hermione Granger', 'Ron Weasley'],
            'helpers': ['Peter Parker', 'Tony Stark', 'Natasha Romanova'],
            'contact': 'hermione@granger.co.uk, rweasley@ministry.gov',
        }

        self.date_serialization_tests = [
            # simple tests
            ('', ''),
            ('empty string', 'empty string'),

            # format-matching
            ('2016-04-18', date(2016, 4, 18)),
            ('2016-04-18T16:41:30', datetime(2016, 4, 18, 16, 41, 30)),
            ('2016-04-18T16:41:30.123',
             datetime(2016, 4, 18, 16, 41, 30, 123000)),
            ('16:41:30', time(16, 41, 30)),
            ('16:41:30.123', time(16, 41, 30, 123000)),

            # format not matching (ie. timezone-aware)
            ('2016-04-18T16:41:30+02:00', '2016-04-18T16:41:30+02:00'),
            ('2016-04-18T14:41:30Z', '2016-04-18T14:41:30Z'),
            ('16:41:30+02:00', '16:41:30+02:00'),
            ('14:41:30Z', '14:41:30Z'),
        ]

    def test_getting_events(self):
        """Ensure only active events with URL are returned."""
        self.fake_cmd.fake_current_events(self.faker, count=6)

        # one active event with URL and one without
        e1, e2 = Event.objects.all()[0:2]
        e1.completed = False  # completed == !active
        e1.url = 'https://swcarpentry.github.io/workshop-template/'
        e1.save()
        e2.completed = False
        e2.url = None
        e2.save()

        # one inactive event with URL and one without
        e3, e4 = Event.objects.all()[2:4]
        e3.completed = True
        e3.url = 'https://datacarpentry.github.io/workshop-template/'
        e3.save()
        e4.completed = True
        e4.url = None
        e4.save()

        # both active but one very old
        e5, e6 = Event.objects.all()[4:6]
        e5.completed = False
        e5.url = 'https://swcarpentry.github.io/workshop-template2/'
        e5.start = date(2014, 1, 1)
        e5.save()
        e6.completed = False
        e6.url = 'https://datacarpentry.github.io/workshop-template2/'
        e6.save()

        # check
        events = set(self.cmd.get_events())
        self.assertEqual({e1, e6}, events)

    def test_parsing_github_url(self):
        """Ensure `parse_github_url()` correctly parses repository URL."""
        url = 'https://github.com/swcarpentry/workshop-template'
        expected = 'swcarpentry', 'workshop-template'
        self.assertEqual(expected, self.cmd.parse_github_url(url))

        with self.assertRaises(WrongWorkshopURL):
            url = 'https://swcarpentry.github.io/workshop-template'
            self.cmd.parse_github_url(url)

    @requests_mock.Mocker()
    def test_getting_event_metadata(self, mock):
        """Ensure metadata are fetched and normalized by `get_event_metadata`."""
        # underlying `fetch_event_tags` and `parse_event_tags` are tested in
        # great detail in `test_util.py`, so here's just a short test
        website_url = 'https://github.com/swcarpentry/workshop-template'
        mock_text = self.mocked_event_page
        mock.get(website_url, text=mock_text, status_code=200)
        # mock placed, let's test `get_event_metadata`

        metadata = self.cmd.get_event_metadata(website_url)
        self.assertEqual(metadata, self.expected_metadata_parsed)

    def test_deserialization_of_string(self):
        "Ensure our datetime matching function works correctly for strings."
        for test, expected in self.date_serialization_tests:
            with self.subTest(test=test):
                self.assertEqual(datetime_match(test), expected)

    def test_deserialization_of_list(self):
        """Ensure our datetime matching function works correctly for lists."""
        tests = self.date_serialization_tests[:]
        tests = list(zip(*tests))  # transpose
        test = list(tests[0])
        expected = list(tests[1])
        self.assertEqual(datetime_decode(test), expected)

    def test_deserialization_of_dict(self):
        """Ensure our datetime matching function works correctly for dicts."""
        test = {k: k for k, v in self.date_serialization_tests}
        expected = {k: v for k, v in self.date_serialization_tests}
        self.assertEqual(datetime_decode(test), expected)

    def test_deserialization_of_nested(self):
        """Ensure our datetime matching function works correctly for nested
        objects/lists."""
        # this test uses simpler format
        dict_test = {'2016-04-18': '2016-04-18'}
        dict_expected = {'2016-04-18': date(2016, 4, 18)}
        test = [dict_test.copy(), dict_test.copy(), dict_test.copy()]
        expected = [dict_expected.copy(), dict_expected.copy(),
                    dict_expected.copy()]
        self.assertEqual(datetime_decode(test), expected)

        test = {'1': test[:]}
        expected = {'1': expected[:]}
        self.assertEqual(datetime_decode(test), expected)

    def test_serialization(self):
        """Ensure serialization uses JSON and works correctly with dates,
        datetimes and times.
        Ensure derialization from JSON works correctly with dates,
        datetimes and times."""
        serialized_json = self.cmd.serialize(self.expected_metadata_parsed)

        self.assertIn('2015-07-13', serialized_json)
        self.assertIn('2015-07-14', serialized_json)
        self.assertIn('2015-07-13-test', serialized_json)
        self.assertIn('-109.045173', serialized_json)
        self.assertIn('36.998977', serialized_json)
        self.assertIn('hermione@granger.co.uk, rweasley@ministry.gov',
                      serialized_json)

        deserialized_data = self.cmd.deserialize(serialized_json)
        self.assertEqual(deserialized_data, self.expected_metadata_parsed)

    @unittest.skip('Don\'t know how to test it')
    def test_loading_from_github(self):
        """Not sure how to test it, so for now leaving this blank."""
        # TODO: mock up github response?
        pass

    @requests_mock.Mocker()
    def test_detecting_changes(self, mock):
        """Make sure tag changes are detected."""
        hash_ = 'abcdefghijklmnopqrstuvwxyz'
        e = Event.objects.create(
            slug='with-changes', host=Host.objects.first(),
            url='https://swcarpentry.github.io/workshop-template/',
            repository_last_commit_hash=hash_,
            repository_metadata='',
            tags_changed=False)

        branch = MagicMock()
        branch.commit = MagicMock()
        branch.commit.sha = hash_

        changes = self.cmd.detect_changes(branch, e)
        self.assertEqual(changes, [])

        # more real example: hash changed
        hash_ = "zyxwvutsrqponmlkjihgfedcba"
        branch.commit.sha = hash_
        mock_text = self.mocked_event_page
        mock.get(e.url, text=mock_text, status_code=200)
        tags = self.cmd.empty_tags()
        tags['instructors'] = self.expected_metadata_parsed['instructors']
        tags['latitude'] = self.expected_metadata_parsed['latitude']
        tags['longitude'] = self.expected_metadata_parsed['longitude']
        e.repository_metadata = self.cmd.serialize(tags)
        e.save()

        changes = self.cmd.detect_changes(branch, e)
        expected = [
            'Helpers changed',
            'Start date changed',
            'End date changed',
            'Country changed',
            'Venue changed',
            'Address changed',
            'Contact details changed',
            'Eventbrite key changed',
        ]
        self.assertEqual(changes, expected)

    @requests_mock.Mocker()
    def test_initialization(self, mock):
        """Make sure events are initialized to sane values."""
        e = Event.objects.create(
            slug='with-changes', host=Host.objects.first(),
            url='https://swcarpentry.github.io/workshop-template/',
            repository_last_commit_hash='', repository_metadata='',
            tags_changed=False, metadata_all_changes='')

        hash_ = 'abcdefghijklmnopqrstuvwxyz'
        branch = MagicMock()
        branch.commit = MagicMock()
        branch.commit.sha = hash_
        mock_text = self.mocked_event_page
        mock.get(e.url, text=mock_text, status_code=200)

        self.cmd.init(branch, e)

        e.refresh_from_db()
        # tags updated
        self.assertEqual(e.repository_last_commit_hash, hash_)
        self.assertEqual(self.cmd.deserialize(e.repository_metadata),
                         self.expected_metadata_parsed)
        self.assertEqual(e.metadata_all_changes, '')
        self.assertEqual(e.tags_changed, False)

    @unittest.skip('This command requires internet connection')
    def test_running(self):
        """Test running whole command."""
        call_command('check_for_workshop_websites_updates')
