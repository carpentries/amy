"""This file contains tests for individual management commands

These commands are run via `./manage.py command`."""

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from workshops.management.commands.upgrade_instructor_profiles import (
    Command as UpgradeInstructorProfileCommand,
    ALL_FIELDS
)
from workshops.models import (
    Airport,
    Role,
    Tag,
    Person,
    Host,
    Event,
    Task,
)

from .base import TestBase


class TestUpgradeInstructorProfile(TestBase):
    def setUp(self):
        super().setUp()
        self.cmd = UpgradeInstructorProfileCommand()

    def test_domains_translation(self):
        "Make sure translating domains from string to list works as expected."
        TEST = [
            (
                'Organismal biology (ecology, botany, zoology, microbiology), '
                'Genetics, genomics, bioinformatics, Computer science/'
                'electrical engineering',
                [
                    'Organismal biology (ecology, botany, zoology, '
                    'microbiology)',
                    'Genetics, genomics, bioinformatics',
                    'Computer science/electrical engineering',
                ]
            ),
            ('Space sciences, Physics', ['Space sciences', 'Physics']),
            ('Chemistry', ['Chemistry']),
            # a case of wrong input (it's possible because instructors can put
            # additional domains):
            ('Neuroscience/Neuroimaging', ['Neuroscience/', 'Neuroimaging']),
            ('', []),
        ]
        for input, expected in TEST:
            assert self.cmd.translate_domains(input) == expected

    def test_lessons_translation(self):
        "Make sure translating lessons from string to list works as expected."
        TEST = [
            (
                'Git (e.g., http://swcarpentry.github.io/git-novice), Make,'
                ' nltk',
                [
                    'swc/git', 'swc/make', 'nltk',
                ]
            ),
            (
                'The Unix Shell (e.g., http://swcarpentry.github.io/shell-'
                'novice), Git (e.g., http://swcarpentry.github.io/git-novice),'
                ' Mercurial (e.g., http://swcarpentry.github.io/hg-novice), '
                'Databases and SQL (e.g., http://swcarpentry.github.io/sql-'
                'novice-survey), Programming with Python (e.g., '
                'http://swcarpentry.github.io/python-novice-inflammation), '
                'Programming with R (e.g., http://swcarpentry.github.io/r-'
                'novice-inflammation)',
                [
                    'swc/shell', 'swc/git', 'swc/hg', 'swc/sql', 'swc/python',
                    'swc/r',
                ]
            ),
            (
                'Data Organization in Spreadsheets (e.g., '
                'http://datacarpentry.github.io/excel-ecology), Data Analysis '
                'and Visualization in R (e.g., http://datacarpentry.github.io'
                '/R-ecology), Databases and SQL (e.g., '
                'https://github.com/datacarpentry/sql-ecology/blob/gh-pages/'
                'sql.md)',
                [
                    'dc/spreadsheets', 'dc/r', 'dc/sql',
                ]
            ),
            (
                'Data Analysis and Visualization in Python (e.g., '
                'http://datacarpentry.github.io/python-ecology), Programming '
                'with R: http://swcarpentry.github.io/r-novice-inflammation',
                [
                    'dc/python', 'swc/r',
                ]
            ),
            ('', []),
        ]
        for input, expected in TEST:
            assert self.cmd.translate_lessons(input) == expected

    def test_gender_translation(self):
        """Make sure different genders yield expected output."""
        TEST = [
            ("Male", "M"),
            ("Female", "F"),
            ("Prefer not to say", "U"),
            ("Genderfluid", "O"),
            ("", "U"),
        ]
        for input, expected in TEST:
            assert self.cmd.translate_gender(input) == expected

    def test_entry_translation(self):
        """Make sure a whole entry is translated correctly."""
        entry_original = {
            'Timestamp': '5/26/2015 22:31:50',
            'Personal (first) name': 'John',
            'Family (last) name': 'Smith',
            'Email address': 'john@smith.com',
            'Nearest major airport': 'FRA',
            'GitHub username': 'johnsmith',
            'Twitter username': 'johnsmith',
            'Personal website': 'http://john.smith.com/',
            'Gender': 'Prefer not to say',
            'Areas of expertise': '',
            'Software Carpentry topics you are comfortable teaching': '',
            'ORCID ID': '000011112222',
            'Data Carpentry lessons you are comfortable teaching': '',
            'Affiliation': 'Smiths CO.',
            'What is your current occupation/career stage?': 'director'
        }
        entry_new = {
            'timestamp': '5/26/2015 22:31:50',
            'personal': 'John',
            'family': 'Smith',
            'email': 'john@smith.com',
            'airport': 'FRA',
            'github': 'johnsmith',
            'twitter': 'johnsmith',
            'url': 'http://john.smith.com/',
            'gender': "U",
            'domains': [],
            'teaching': [],
            'orcid': '000011112222',
            'affiliation': 'Smiths CO.',
            'position': 'director'
        }
        assert self.cmd.translate(entry_original) == entry_new

    def test_check_entry(self):
        """Make sure entry is well checked for any discrepancies."""

        # check missing fields
        entry = {}
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert not correct
        assert "Missing fields" in errors[0]

        # check empty required fields
        entry = {
            'timestamp': '', 'personal': '', 'family': '', 'email': '',
            'airport': '', 'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert not correct
        assert "Missing fields" not in errors[0]
        assert "Required field" in errors[0] and "is empty" in errors[0]

        # check matching person by email
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.co.uk', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert correct

        # check matching person by name
        entry = {
            'timestamp': '', 'personal': 'Hermione', 'family': 'Granger',
            'email': 'hermione@granger.com', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert correct

        # check matching >=2 persons by name
        Person.objects.create(
            personal='Hermione', middle=None, family='Granger', gender='F',
            airport=self.airport_0_0, email='hermione@granger.eu'
        )
        entry = {
            'timestamp': '', 'personal': 'Hermione', 'family': 'Granger',
            'email': 'hermione@granger.com', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert not correct
        assert 'There are multiple users with this name' in errors[0]

        # check non-existing person
        entry = {
            'timestamp': '', 'personal': 'Lord', 'family': 'Voldemort',
            'email': 'lord@voldemort.com', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert not correct
        assert 'User with either this email' in errors[0]
        assert 'or this name' in errors[0]
        assert 'does not exist' in errors[0]

        # check non-instructor person
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.eu', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert correct  # we want people even though they aren't instructors
        assert 'This person does not have any instructor badge' in warnings[0]

        # check non-existing airport
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.co.uk', 'airport': 'ABC',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert not correct
        assert 'Airport "ABC" does not exist' in errors[0]

        # check presence of lessons
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.co.uk', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': ['asd/python', 'swc/git'],
            'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, errors, warnings = self.cmd.check_entry(entry)
        assert not correct
        errors = "".join(errors)
        assert 'Lesson' in errors
        assert 'asd/python' in errors
        assert 'does not exist' in errors
        assert 'swc/git' not in errors

        # check correct entry
        correct_entry = {
            'timestamp': '5/26/2015 22:31:50',
            'personal': 'Hermione',
            'family': 'Granger',
            'email': 'hermione@granger.co.uk',
            'airport': 'AAA',
            'github': 'hermionegranger',
            'twitter': 'hermionegranger',
            'url': 'http://hermione.granger.co.uk/',
            'gender': "O",
            'domains': [],
            'teaching': [],
            'orcid': '000011112222',
            'affiliation': 'Hogwart CO.',
            'position': 'undergraduate'
        }
        correct, errors, warnings = self.cmd.check_entry(correct_entry)
        assert correct
        assert errors == []

    def test_update(self):
        """Make sure entries are indeed updated."""
        allowed_fields = ALL_FIELDS

        assert self.hermione.github != 'hermionegranger'
        assert self.hermione.lessons.all().count() != 0

        correct_entry = {
            'timestamp': '5/26/2015 22:31:50',
            'personal': 'Hermione',
            'family': 'Granger',
            'email': 'hermione@granger.co.uk',
            'airport': 'AAA',
            'github': 'hermionegranger',
            'twitter': 'hermionegranger',
            'url': 'http://hermione.granger.co.uk/',
            'gender': "O",
            'domains': [],
            'teaching': [],
            'orcid': '000011112222',
            'affiliation': 'Hogwart CO.',
            'position': 'undergraduate'
        }
        correct, errors, warnings = self.cmd.check_entry(correct_entry)
        assert correct
        self.cmd.update(correct_entry, allowed_fields=allowed_fields)

        self.hermione.refresh_from_db()
        assert self.hermione.github == 'hermionegranger'
        assert self.hermione.affiliation == 'Hogwart CO.'
        assert self.hermione.lessons.all().count() == 0

    def test_update_no_affiliation(self):
        """Ensure no affiliation yields correct empty string after update."""
        allowed_fields = ALL_FIELDS

        correct_entry = {
            'timestamp': '5/26/2015 22:31:50',
            'personal': 'Hermione',
            'family': 'Granger',
            'email': 'hermione@granger.co.uk',
            'airport': 'AAA',
            'github': 'hermionegranger',
            'twitter': 'hermionegranger',
            'url': 'http://hermione.granger.co.uk/',
            'gender': "O",
            'domains': [],
            'teaching': [],
            'orcid': '000011112222',
            'affiliation': '',
            'position': 'undergraduate'
        }
        correct, errors, warnings = self.cmd.check_entry(correct_entry)
        assert correct
        self.cmd.update(correct_entry, allowed_fields=allowed_fields)

        self.hermione.refresh_from_db()
        assert self.hermione.affiliation == ''

    def test_update_subset_of_fields(self):
        """We can update specific fields."""
        allowed_fields = ['family', 'affiliation']

        correct_entry = {
            'timestamp': '5/26/2015 22:31:50',
            'personal': 'Hermione-the-Conjurer',
            'family': 'Grangerdaughter',
            'email': 'hermione@granger.co.uk',
            'airport': 'AAA',
            'github': 'hermionegranger',
            'twitter': 'hermionegranger',
            'url': 'http://hermione.granger.co.uk/',
            'gender': "O",
            'domains': [],
            'teaching': [],
            'orcid': '000011112222',
            'affiliation': 'Hogwart The School of Wizardry',
            'position': 'undergraduate'
        }
        correct, errors, warnings = self.cmd.check_entry(correct_entry)
        assert correct
        self.cmd.update(correct_entry, allowed_fields=allowed_fields)

        self.hermione.refresh_from_db()
        assert self.hermione.affiliation == 'Hogwart The School of Wizardry'
        assert self.hermione.personal == 'Hermione'
        assert self.hermione.family == 'Grangerdaughter'

    def test_process(self):
        """Make sure the command works well with CSVs (even ill-formatted)."""
        # we'll only test immunity to ill-formatted CSVs, not if they succeed
        # in updating instructors
        FN = [
            'workshops/test/upgrade_instructor_profiles1.csv',
            'workshops/test/upgrade_instructor_profiles2.csv',
            'workshops/test/upgrade_instructor_profiles3.csv',
        ]

        correct_list = []
        for fname in FN:
            with open(fname, 'r') as f:
                # A little hack: in "for-else" with generators "else" clause is
                # always evaluated at StopIteration, ie. when generator runs
                # out.
                # This works because our only test files contain at most only
                # 1 entry.
                correct = False
                for entry in self.cmd.process(f):
                    correct, _, _ = self.cmd.check_entry(entry)
                else:
                    # empty file
                    correct_list.append(correct)

        assert correct_list == [True, False, False], correct_list

    def test_output(self):
        """Make sure the command works well."""

        def stringify_streams(stream1, stream2):
            stream1.seek(0)
            stream2.seek(0)
            return stream1.read(), stream2.read()

        call_args = [
            (
                'workshops/test/upgrade_instructor_profiles1.csv',
                {'force': False}
            ),
            (
                'workshops/test/upgrade_instructor_profiles2.csv',
                {'force': False}
            ),
            (
                'workshops/test/upgrade_instructor_profiles3.csv',
                {'force': False}
            ),
            (
                'workshops/test/upgrade_instructor_profiles4.csv',
                {'force': True}
            ),
        ]

        # 1st file: all correct
        positional, options = call_args[0]
        stdout = StringIO()
        stderr = StringIO()
        call_command('upgrade_instructor_profiles', positional,
                     stdout=stdout, stderr=stderr, **options)
        stdout, stderr = stringify_streams(stdout, stderr)
        assert 'ERROR' not in stderr
        assert 'WARNING' not in stdout

        # 2nd file: no input
        positional, options = call_args[1]
        stdout = StringIO()
        stderr = StringIO()
        call_command('upgrade_instructor_profiles', positional,
                     stdout=stdout, stderr=stderr, **options)
        stdout, stderr = stringify_streams(stdout, stderr)
        assert 'ERROR' not in stderr
        assert 'WARNING' not in stdout

        # 3rd file: missing some fields
        positional, options = call_args[2]
        stdout = StringIO()
        stderr = StringIO()
        call_command('upgrade_instructor_profiles', positional,
                     stdout=stdout, stderr=stderr, **options)
        stdout, stderr = stringify_streams(stdout, stderr)
        assert 'row 1' in stderr
        assert 'ERROR' in stderr

        # 4th file: first entry correct, second has missing lesson 'ruby'
        positional, options = call_args[3]
        stdout = StringIO()
        stderr = StringIO()
        call_command('upgrade_instructor_profiles', positional,
                     stdout=stdout, stderr=stderr, **options)
        stdout, stderr = stringify_streams(stdout, stderr)
        assert 'row 2' in stderr
        assert 'ERROR' in stderr
        assert 'ruby' in stderr


class TestFakeDatabaseCommand(TestCase):
    def setUp(self):
        self.cmd = UpgradeInstructorProfileCommand()
        self.seed = 12345

    def test_no_airports_created(self):
        """Make sure we don't create any airports.

        We don't want to create them, because data migrations add some, and in
        the future we want to add them via fixture (see #626)."""
        airports_before = set(Airport.objects.all())
        call_command('fake_database', seed=self.seed)
        airports_after = set(Airport.objects.all())

        self.assertEqual(airports_before, airports_after)

    def test_new_roles_added(self):
        """Make sure we add roles that are hard-coded. They'll end up in
        fixtures in future (see #626)."""
        roles = ['helper', 'instructor', 'host', 'learner', 'organizer',
                 'tutor', 'debriefed']
        self.assertFalse(Role.objects.filter(name__in=roles).exists())
        call_command('fake_database', seed=self.seed)

        self.assertEqual(set(roles),
                         set(Role.objects.values_list('name', flat=True)))

    def test_new_tags_added(self):
        """Make sure we add tags that are hard-coded. They'll end up in
        fixtures in future (see #626)."""
        tags = ['SWC', 'DC', 'LC', 'WiSE', 'TTT', 'online', 'stalled',
                'unresponsive']
        self.assertNotEqual(set(tags),
                            set(Tag.objects.values_list('name', flat=True)))

        call_command('fake_database', seed=self.seed)
        self.assertEqual(set(tags),
                         set(Tag.objects.values_list('name', flat=True)))

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
