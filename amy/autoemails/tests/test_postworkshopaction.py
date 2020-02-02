from datetime import timedelta, date

from django.test import TestCase

from autoemails.actions import PostWorkshopAction
from autoemails.models import Trigger, EmailTemplate
from workshops.models import Task, Role, Person, Event, Tag, Organization


class TestPostWorkshopAction(TestCase):
    def setUp(self):
        Tag.objects.bulk_create([
            Tag(name='SWC'),
            Tag(name='DC'),
            Tag(name='LC'),
            Tag(name='TTT'),
        ])

    def testLaunchAt(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        a = PostWorkshopAction(trigger=Trigger(action='test-action',
                                               template=EmailTemplate()))
        self.assertEqual(a.get_launch_at(), timedelta(minutes=10))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake Task, Role and Event data
        e = Event.objects.create(
            slug='test-event',
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e.tags.set(Tag.objects.filter(name__in=['LC', 'TTT']))
        p = Person.objects.create(personal='Harry', family='Potter',
                                  email='hp@magic.uk')
        r = Role.objects.create(name='host')
        Task.objects.create(event=e, person=p, role=r)

        # 1st case: everything is good
        self.assertEqual(PostWorkshopAction.check(e), True)

        # 2nd case: event has no start date
        # result: OK
        e.start = None
        e.save()
        self.assertEqual(PostWorkshopAction.check(e), True)

        # 3rd case: event has no end date
        # result: FAIL
        e.end = None
        e.save()
        self.assertEqual(PostWorkshopAction.check(e), False)

        # bring back the good date
        e.end = date.today() + timedelta(days=8)
        e.save()
        self.assertEqual(PostWorkshopAction.check(e), True)

        # 4th case: event is tagged with one (or more) excluding tags
        # result: FAIL
        for tag in ['cancelled', 'stalled', 'unresponsive']:
            e.tags.add(Tag.objects.get(name=tag))
            self.assertEqual(PostWorkshopAction.check(e), False)
            e.tags.remove(Tag.objects.get(name=tag))

        # retest to make sure it's back to normal
        self.assertEqual(PostWorkshopAction.check(e), True)

        # 5th case: no host/instructor tasks
        # This is tricky case. Sometimes the workshop can be defined before
        # there are any instructor/host tasks.
        # result: OK
        r.name = 'helper'
        r.save()
        self.assertEqual(PostWorkshopAction.check(e), True)
        r.name = 'instructor'  # additionally check for instructor role
        r.save()

        # retest to make sure it's back to normal
        # (note: role was changed to "instructor")
        self.assertEqual(PostWorkshopAction.check(e), True)

    def testContext(self):
        """Make sure `get_additional_context` works correctly."""
        a = PostWorkshopAction(trigger=Trigger(action='test-action',
                                               template=EmailTemplate()))

        # method fails when obligatory objects are missing
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'event'
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
        e.tags.set(Tag.objects.filter(name__in=['TTT', 'SWC']))
        p1 = Person.objects.create(personal='Harry', family='Potter',
                                   username='hpotter',
                                   email='hp@magic.uk')
        p2 = Person.objects.create(personal='Hermione', family='Granger',
                                   username='hgranger',
                                   email='hg@magic.uk')
        p3 = Person.objects.create(personal='Ron', family='Weasley',
                                   username='rweasley',
                                   email='rw@magic.uk')
        host = Role.objects.create(name='host')
        instructor = Role.objects.create(name='instructor')
        helper = Role.objects.create(name='helper')
        Task.objects.bulk_create([
            Task(event=e, person=p1, role=host),
            Task(event=e, person=p2, role=instructor),
            Task(event=e, person=p3, role=helper),
            Task(event=e, person=p1, role=helper),
        ])

        ctx = a.get_additional_context(objects=dict(event=e))
        self.assertEqual(
            ctx,
            dict(
                workshop=e,
                workshop_main_type='SWC',
                dates=e.human_readable_date,
                host=Organization.objects.first(),
                regional_coordinator_email=['admin-uk@carpentries.org'],
                helpers=[p1, p3],
                all_emails=['hp@magic.uk', 'hg@magic.uk'],
                assignee='Regional Coordinator',
            ),
        )
