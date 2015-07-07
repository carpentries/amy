"""This file contains tests for individual management commands

These commands are run via `./manage.py command`."""

from workshops.management.commands.upgrade_instructor_profiles import Command
from workshops.models import Person

from .base import TestBase


class TestUpgradeInstructorProfile(TestBase):
    def setUp(self):
        super().setUp()
        self.cmd = Command()

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
                    'dc/spreadsheet', 'dc/r', 'dc/sql',
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
            ("Prefer not to say", "O"),
            ("Genderfluid", "O"),
            ("", None),
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
            'gender': "O",
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
        correct, reasons = self.cmd.check_entry(entry)
        assert not correct
        assert "Missing fields" in reasons[0]

        # check empty required fields
        entry = {
            'timestamp': '', 'personal': '', 'family': '', 'email': '',
            'airport': '', 'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, reasons = self.cmd.check_entry(entry)
        assert not correct
        assert "Missing fields" not in reasons[0]
        assert "Required field" in reasons[0] and "is empty" in reasons[0]

        # check matching person by email
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.co.uk', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, reasons = self.cmd.check_entry(entry)
        assert correct

        # check matching person by name
        entry = {
            'timestamp': '', 'personal': 'Hermione', 'family': 'Granger',
            'email': 'hermione@granger.com', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, reasons = self.cmd.check_entry(entry)
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
        correct, reasons = self.cmd.check_entry(entry)
        assert not correct
        assert 'There are multiple users with this name' in reasons[0]

        # check non-existing person
        entry = {
            'timestamp': '', 'personal': 'Lord', 'family': 'Voldemort',
            'email': 'lord@voldemort.com', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, reasons = self.cmd.check_entry(entry)
        assert not correct
        assert 'User with either this email' in reasons[0]
        assert 'or this name' in reasons[0]
        assert 'does not exist' in reasons[0]

        # check non-instructor person
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.eu', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, reasons = self.cmd.check_entry(entry)
        assert not correct
        assert 'This person does not have an instructor badge' in reasons[0]

        # check non-existing airport
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.co.uk', 'airport': 'ABC',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': '', 'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, reasons = self.cmd.check_entry(entry)
        assert not correct
        assert 'Airport with this IATA code' in reasons[0]
        assert 'does not exist' in reasons[0]

        # check presence of lessons
        entry = {
            'timestamp': '', 'personal': 'H', 'family': 'G',
            'email': 'hermione@granger.co.uk', 'airport': 'AAA',
            'github': '', 'twitter': '', 'url': '',
            'gender': '', 'domains': '', 'teaching': ['asd/python', 'swc/git'],
            'orcid': '',
            'affiliation': '', 'position': '',
        }
        correct, reasons = self.cmd.check_entry(entry)
        assert not correct
        reasons = "".join(reasons)
        assert 'Lesson' in reasons
        assert 'asd/python' in reasons
        assert 'does not exist' in reasons
        assert 'swc/git' not in reasons

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
        correct, reasons = self.cmd.check_entry(correct_entry)
        assert correct
        assert reasons == []

    def test_update(self):
        """Make sure entries are indeed updated."""
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
        correct, reasons = self.cmd.check_entry(correct_entry)
        assert correct
        self.cmd.update(correct_entry)

        self.hermione.refresh_from_db()
        assert self.hermione.github == 'hermionegranger'
        assert self.hermione.lessons.all().count() == 0

    def test_process(self):
        """Make sure the Command works well with CSVs (even ill-formatted)."""
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
                    correct, _ = self.cmd.check_entry(entry)
                else:
                    # empty file
                    correct_list.append(correct)

        assert correct_list == [True, False, False], correct_list
