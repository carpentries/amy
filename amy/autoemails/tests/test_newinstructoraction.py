from datetime import timedelta, date

from django.test import TestCase

from autoemails.actions import NewInstructorAction
from autoemails.models import Trigger, EmailTemplate
from workshops.models import Task, Role, Person, Event, Tag, Organization


class TestNewInstructorAction(TestCase):
    def setUp(self):
        Tag.objects.bulk_create([
            Tag(name='SWC'),
            Tag(name='DC'),
            Tag(name='LC'),
        ])

    def testLaunchAt(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        a = NewInstructorAction(trigger=Trigger(action='test-action',
                                                template=EmailTemplate()))
        self.assertEqual(a.get_launch_at(), timedelta(hours=1))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake Task, Role and Event data
        e = Event.objects.create(
            slug='test-event',
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country='GB',
            venue='Ministry of Magic',
            address='Underground',
            latitude=20.0,
            longitude=20.0,
            url='https://test-event.example.com',
        )
        e.tags.set(Tag.objects.filter(name__in=['SWC', 'DC', 'LC']))
        p = Person(personal='Harry', family='Potter', email='hp@magic.uk')
        r = Role(name='instructor')
        t = Task(event=e, person=p, role=r)

        # 1st case: everything is good
        self.assertEqual(NewInstructorAction.check(t), True)

        # 2nd case: event is no longer marked as "upcoming"
        e.url = None
        e.save()
        self.assertEqual(NewInstructorAction.check(t), False)
        e.url = 'https://test-event.example.com'
        e.save()

        # 3rd case: event is tagged with one (or more) excluding tags
        e.tags.add(Tag.objects.get(name='cancelled'))
        self.assertEqual(NewInstructorAction.check(t), False)
        e.tags.remove(Tag.objects.get(name='cancelled'))

        # 4th case: role is different than 'instructor'
        r.name = 'helper'
        self.assertEqual(NewInstructorAction.check(t), False)
        r.name = 'instructor'

    def testCheckForNonContactablePerson(self):
        """Make sure `may_contact` doesn't impede `check()`."""
        # totally fake Task, Role and Event data
        e = Event.objects.create(
            slug='test-event',
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country='GB',
            venue='Ministry of Magic',
            address='Underground',
            latitude=20.0,
            longitude=20.0,
            url='https://test-event.example.com',
        )
        e.tags.set(Tag.objects.filter(name__in=['SWC', 'DC', 'LC']))
        p = Person(personal='Harry', family='Potter', email='hp@magic.uk',
                   may_contact=True)  # contact allowed
        r = Role(name='instructor')
        t = Task(event=e, person=p, role=r)
        self.assertEqual(NewInstructorAction.check(t), True)
        p.may_contact = False  # contact disallowed
        self.assertEqual(NewInstructorAction.check(t), True)

    def testContext(self):
        """Make sure `get_additional_context` works correctly."""

        a = NewInstructorAction(trigger=Trigger(action='test-action',
                                                template=EmailTemplate()))

        # method fails when obligatory objects are missing
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'event'
        with self.assertRaises(KeyError):
            a.get_additional_context(dict(event='dummy'))  # missing 'task'
        with self.assertRaises(AttributeError):
            # now both objects are present, but the method tries to execute
            # `refresh_from_db` on them
            a.get_additional_context(dict(event='dummy', task='dummy'))

        e = Event.objects.create(
            slug='test-event',
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country='GB',
            venue='Ministry of Magic',
            address='Underground',
            latitude=20.0,
            longitude=20.0,
            url='https://test-event.example.com',
        )
        e.tags.set(Tag.objects.filter(name__in=['SWC', 'DC', 'LC']))
        p = Person.objects.create(personal='Harry', family='Potter',
                                  email='hp@magic.uk')
        r = Role.objects.create(name='instructor')
        t = Task.objects.create(event=e, person=p, role=r)

        ctx = a.get_additional_context(objects=dict(event=e, task=t))
        self.assertEqual(
            ctx,
            dict(
                workshop=e,
                workshop_main_type='SWC',
                dates=e.human_readable_date,
                host=Organization.objects.first(),
                regional_coordinator_email=['admin-uk@carpentries.org'],
                person=p,
                instructor=p,
                role=r,
                assignee='Regional Coordinator',
            ),
        )
