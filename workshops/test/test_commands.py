"""This file contains tests for individual management commands

These commands are run via `./manage.py command`."""

from datetime import date

from django.core.management import call_command
from django.test import TestCase

from workshops.management.commands.fake_database import (
    Command as FakeDatabaseCommand,
    Faker
)
from ..management.commands.instructors_activity import \
    Command as InstructorsActivityCommand

from .base import TestBase
from workshops.models import (
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
                'unresponsive','hackathon']
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
