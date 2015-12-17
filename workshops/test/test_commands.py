"""This file contains tests for individual management commands

These commands are run via `./manage.py command`."""

from django.core.management import call_command
from django.test import TestCase

from workshops.management.commands.fake_database import (
    Command as FakeDatabaseCommand,
    Faker
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
                'unresponsive']
        self.assertNotEqual(set(tags),
                            set(Tag.objects.values_list('name', flat=True)))

        self.cmd.fake_tags(self.faker)
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
