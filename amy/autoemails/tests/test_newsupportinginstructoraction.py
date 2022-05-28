from datetime import date, timedelta

from django.test import TestCase

from autoemails.actions import NewSupportingInstructorAction
from autoemails.models import EmailTemplate, Trigger
from workshops.models import Event, Organization, Person, Role, Tag, Task


class TestNewSupportingInstructorAction(TestCase):
    def setUp(self):
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="automated-email"),
            ]
        )
        Organization.objects.bulk_create(
            [
                Organization(
                    domain="librarycarpentry.org", fullname="Library Carpentry"
                ),
                Organization(domain="datacarpentry.org", fullname="Data Carpentry"),
                Organization(
                    domain="software-carpentry.org", fullname="Software Carpentry"
                ),
                Organization(domain="carpentries.org", fullname="Instructor Training"),
            ]
        )
        Role.objects.create(name="supporting-instructor")

    def testLaunchAt(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        a = NewSupportingInstructorAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )
        self.assertEqual(a.get_launch_at(), timedelta(hours=1))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake Task, Role and Event data
        LC_org = Organization.objects.get(domain="librarycarpentry.org")
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=LC_org,
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e.tags.set(Tag.objects.filter(name__in=["SWC", "DC", "LC", "automated-email"]))
        p = Person(personal="Harry", family="Potter", email="hp@magic.uk")
        r = Role(name="supporting-instructor")
        t = Task(event=e, person=p, role=r)

        # 1st case: everything is good
        self.assertEqual(NewSupportingInstructorAction.check(t), True)

        # 2nd case: event has no start date, but still valid tags
        e.start = None
        e.save()
        self.assertEqual(NewSupportingInstructorAction.check(t), True)

        # 3rd case: event start date in past, but still valid tags
        e.start = date(2000, 1, 1)
        e.save()
        self.assertEqual(NewSupportingInstructorAction.check(t), False)

        # bring back the good date
        e.start = date.today() + timedelta(days=7)
        e.save()
        self.assertEqual(NewSupportingInstructorAction.check(t), True)

        # 4th case: event is tagged with one (or more) excluding tags
        e.tags.add(Tag.objects.get(name="cancelled"))
        self.assertEqual(NewSupportingInstructorAction.check(t), False)
        e.tags.remove(Tag.objects.get(name="cancelled"))

        # 5th case: role is different than 'supporting-instructor'
        r.name = "helper"
        self.assertEqual(NewSupportingInstructorAction.check(t), False)
        r.name = "supporting-instructor"

        # 6th case: no administrator
        e.administrator = None
        e.save()
        self.assertEqual(NewSupportingInstructorAction.check(t), False)
        e.administrator = LC_org

        # 7th case: wrong administrator (self organized or instructor training)
        e.administrator = Organization.objects.get(domain="self-organized")
        e.save()
        self.assertEqual(NewSupportingInstructorAction.check(t), False)
        e.administrator = Organization.objects.get(domain="carpentries.org")
        e.save()
        self.assertEqual(NewSupportingInstructorAction.check(t), False)

    def testCheckForNonContactablePerson(self):
        """Make sure `may_contact` doesn't impede `check()`."""
        # totally fake Task, Role and Event data
        LC_org = Organization.objects.get(domain="librarycarpentry.org")
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=LC_org,
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
            address="Underground",
            latitude=20.0,
            longitude=20.0,
            url="https://test-event.example.com",
        )
        e.tags.set(Tag.objects.filter(name__in=["SWC", "DC", "LC", "automated-email"]))
        p = Person(
            personal="Harry", family="Potter", email="hp@magic.uk", may_contact=True
        )  # contact allowed
        r = Role(name="supporting-instructor")
        t = Task(event=e, person=p, role=r)
        self.assertEqual(NewSupportingInstructorAction.check(t), True)
        p.may_contact = False  # contact disallowed
        self.assertEqual(NewSupportingInstructorAction.check(t), True)

    def testContext(self):
        """Make sure `get_additional_context` works correctly."""

        a = NewSupportingInstructorAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )

        # method fails when obligatory objects are missing
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'event'
        with self.assertRaises(KeyError):
            a.get_additional_context(dict(event="dummy"))  # missing 'task'
        with self.assertRaises(AttributeError):
            # now both objects are present, but the method tries to execute
            # `refresh_from_db` on them
            a.get_additional_context(dict(event="dummy", task="dummy"))

        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
            address="Underground",
            latitude=20.0,
            longitude=20.0,
            url="https://test-event.example.com",
        )
        e.tags.set(Tag.objects.filter(name="SWC"))
        p = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="supporting-instructor")
        t = Task.objects.create(event=e, person=p, role=r)

        ctx = a.get_additional_context(objects=dict(event=e, task=t))
        self.assertEqual(
            ctx,
            dict(
                workshop=e,
                workshop_main_type="SWC",
                dates=e.human_readable_date(),
                host=Organization.objects.first(),
                regional_coordinator_email=["admin-uk@carpentries.org"],
                person=p,
                instructor=p,
                role=r,
                task=t,
                assignee="Regional Coordinator",
                tags=["SWC"],
            ),
        )

    def test_event_slug(self):
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
            address="Underground",
            latitude=20.0,
            longitude=20.0,
            url="https://test-event.example.com",
        )
        e.tags.set(Tag.objects.filter(name="SWC"))
        p = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="supporting-instructor")
        t = Task.objects.create(event=e, person=p, role=r)

        a = NewSupportingInstructorAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e, task=t),
        )

        self.assertEqual(a.event_slug(), "test-event")

    def test_all_recipients(self):
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
            address="Underground",
            latitude=20.0,
            longitude=20.0,
            url="https://test-event.example.com",
        )
        e.tags.set(Tag.objects.filter(name="SWC"))
        p = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="supporting-instructor")
        t = Task.objects.create(event=e, person=p, role=r)

        a = NewSupportingInstructorAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e, task=t),
        )

        self.assertEqual(a.all_recipients(), "hp@magic.uk")
