from datetime import timedelta, date

from django.test import TestCase

from autoemails.actions import InstructorsHostIntroductionAction
from autoemails.models import Trigger, EmailTemplate
from workshops.fields import TAG_SEPARATOR
from workshops.models import (
    Task,
    Role,
    Person,
    Event,
    Tag,
    Organization,
)


class TestInstructorsHostIntroductionAction(TestCase):
    def setUp(self):
        # we're missing some tags
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="TTT"),
                Tag(name="automated-email"),
            ]
        )
        # by default there's only self-organized organization
        Organization.objects.bulk_create(
            [Organization(domain="carpentries.org", fullname="Instructor Training"),]
        )

        self.host = Role.objects.create(name="host")
        self.instructor = Role.objects.create(name="instructor")
        self.supporting_instructor = Role.objects.create(name="supporting-instructor")

        self.person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", username="hp",
        )
        self.person2 = Person.objects.create(
            personal="Ron", family="Weasley", email="rw@magic.uk", username="rw",
        )
        self.person3 = Person.objects.create(
            personal="Hermione", family="Granger", email="hg@magic.uk", username="hg",
        )
        self.person4 = Person.objects.create(
            personal="Peter",
            family="Parker",
            email="peter@webslinger.net",
            username="spiderman",
        )
        self.person5 = Person.objects.create(
            personal="Tony", family="Stark", email="me@stark.com", username="ironman",
        )

    def testLaunchAt(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        trigger = Trigger(action="test-action", template=EmailTemplate())
        a = InstructorsHostIntroductionAction(trigger=trigger)
        self.assertEqual(a.get_launch_at(), timedelta(hours=1))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake events
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        e2 = Event.objects.create(slug="bogus-event", host=Organization.objects.first())
        # tasks
        host = Task.objects.create(person=self.person1, role=self.host, event=e,)
        instructor1 = Task.objects.create(
            person=self.person2, role=self.instructor, event=e,
        )
        instructor2 = Task.objects.create(
            person=self.person3, role=self.instructor, event=e,
        )

        # 1st case: everything is good
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 2nd case: event has no start date
        # result: FAIL
        e.start = None
        e.save()
        self.assertEqual(InstructorsHostIntroductionAction.check(e), False)

        # bring back the good date
        e.start = date.today() + timedelta(days=7)
        e.save()
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 3rd case: event is tagged with one (or more) excluding tags
        # result: FAIL
        for tag in ["cancelled", "stalled", "unresponsive"]:
            e.tags.add(Tag.objects.get(name=tag))
            self.assertEqual(InstructorsHostIntroductionAction.check(e), False)
            e.tags.remove(Tag.objects.get(name=tag))

        # retest to make sure it's back to normal
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 4th case: no administrator
        # result: FAIL
        e.administrator = None
        e.save()
        self.assertEqual(InstructorsHostIntroductionAction.check(e), False)
        e.administrator = Organization.objects.get(domain="carpentries.org")
        e.save()

        # retest to make sure it's back to normal
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 5th case: wrong administrator (self organised)
        # result: FAIL
        e.administrator = Organization.objects.get(domain="self-organized")
        e.save()
        self.assertEqual(InstructorsHostIntroductionAction.check(e), False)

        # retest to make sure it's back to normal
        e.administrator = Organization.objects.get(domain="carpentries.org")
        e.save()
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 6th case: missing host, instructor1, or instructor2
        for task in [host, instructor1, instructor2]:
            task.event = e2
            task.save()
            self.assertEqual(InstructorsHostIntroductionAction.check(e), False)
            task.event = e
            task.save()
            self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 7th case: more than 2 instructors - should still work
        Task.objects.create(
            person=self.person1, role=self.instructor, event=e,
        )
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 8th case: for online require also 1 supporting instructor
        e.tags.add(Tag.objects.get(name="online"))
        self.assertEqual(InstructorsHostIntroductionAction.check(e), False)
        Task.objects.create(
            person=self.person4, role=self.supporting_instructor, event=e,
        )
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

        # 9th case: for online, more than 1 supporting instructors should still work
        Task.objects.create(
            person=self.person5, role=self.supporting_instructor, event=e,
        )
        self.assertEqual(InstructorsHostIntroductionAction.check(e), True)

    def testContext(self):
        """Make sure `get_additional_context` works correctly."""
        a = InstructorsHostIntroductionAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )

        # method fails when obligatory objects are missing
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'event'
        with self.assertRaises(AttributeError):
            # now event is present, but the method tries to execute `refresh_from_db`
            # on it
            a.get_additional_context(dict(event="dummy"))

        # totally fake Event
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            contact=TAG_SEPARATOR.join(["test@hogwart.com", "test2@magic.uk"]),
            country="GB",
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        # tasks
        host = Task.objects.create(person=self.person1, role=self.host, event=e)
        instructor1 = Task.objects.create(
            person=self.person2, role=self.instructor, event=e,
        )
        instructor2 = Task.objects.create(
            person=self.person3, role=self.instructor, event=e,
        )
        supporting_instructor1 = Task.objects.create(
            person=self.person4, role=self.supporting_instructor, event=e,
        )
        supporting_instructor2 = Task.objects.create(
            person=self.person5, role=self.supporting_instructor, event=e,
        )

        ctx = a.get_additional_context(objects=dict(event=e))
        self.maxDiff = None
        expected = dict(
            workshop=e,
            workshop_main_type="LC",
            dates=e.human_readable_date,
            workshop_host=Organization.objects.first(),
            regional_coordinator_email=["admin-uk@carpentries.org"],
            host=host.person,
            instructors=[instructor1.person, instructor2.person],
            instructor1=instructor1.person,
            instructor2=instructor2.person,
            supporting_instructors=[
                supporting_instructor1.person,
                supporting_instructor2.person,
            ],
            supporting_instructor1=supporting_instructor1.person,
            supporting_instructor2=supporting_instructor2.person,
            all_emails=[
                "hp@magic.uk",
                "rw@magic.uk",
                "hg@magic.uk",
                "peter@webslinger.net",
                "me@stark.com",
                "test@hogwart.com",
                "test2@magic.uk",
            ],
            assignee="Regional Coordinator",
            tags=["LC", "automated-email"],
        )
        self.assertEqual(ctx, expected)

    def testContextEmptyContact(self):
        """Make sure `get_additional_context` works correctly when contacts are empty
        for the event."""
        a = InstructorsHostIntroductionAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )

        # totally fake Event
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            contact="",
            country="GB",
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        # tasks
        host = Task.objects.create(person=self.person1, role=self.host, event=e)
        instructor1 = Task.objects.create(
            person=self.person2, role=self.instructor, event=e,
        )
        instructor2 = Task.objects.create(
            person=self.person3, role=self.instructor, event=e,
        )
        supporting_instructor1 = Task.objects.create(
            person=self.person4, role=self.supporting_instructor, event=e,
        )
        supporting_instructor2 = Task.objects.create(
            person=self.person5, role=self.supporting_instructor, event=e,
        )

        ctx = a.get_additional_context(objects=dict(event=e))
        self.maxDiff = None
        expected = dict(
            workshop=e,
            workshop_main_type="LC",
            dates=e.human_readable_date,
            workshop_host=Organization.objects.first(),
            regional_coordinator_email=["admin-uk@carpentries.org"],
            host=host.person,
            instructors=[instructor1.person, instructor2.person],
            instructor1=instructor1.person,
            instructor2=instructor2.person,
            supporting_instructors=[
                supporting_instructor1.person,
                supporting_instructor2.person,
            ],
            supporting_instructor1=supporting_instructor1.person,
            supporting_instructor2=supporting_instructor2.person,
            all_emails=[
                "hp@magic.uk",
                "rw@magic.uk",
                "hg@magic.uk",
                "peter@webslinger.net",
                "me@stark.com",
            ],
            assignee="Regional Coordinator",
            tags=["LC", "automated-email"],
        )
        self.assertEqual(ctx, expected)

    def testRecipients(self):
        """Make sure InstructorsHostIntroductionAction correctly renders recipients.

        They should get overwritten by InstructorsHostIntroductionAction during email
        building."""
        # totally fake Event
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            contact=TAG_SEPARATOR.join(["test@hogwart.com", "test2@magic.uk"]),
            country="GB",
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        # tasks
        Task.objects.create(person=self.person1, role=self.host, event=e)
        Task.objects.create(
            person=self.person2, role=self.instructor, event=e,
        )
        Task.objects.create(
            person=self.person3, role=self.instructor, event=e,
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome to {{ site.name }}",
            to_header="recipient@address.com",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="{{ reply_to }}",
            body_template="Sample text.",
        )
        trigger = Trigger.objects.create(
            action="self-organised-request-form", template=template,
        )
        a = InstructorsHostIntroductionAction(trigger=trigger, objects=dict(event=e),)
        email = a._email()
        self.assertEqual(
            email.to,
            [
                "hp@magic.uk",
                "rw@magic.uk",
                "hg@magic.uk",
                "test@hogwart.com",
                "test2@magic.uk",
            ],
        )

    def test_event_slug(self):
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
        )
        e.tags.set(Tag.objects.filter(name="LC"))

        a = InstructorsHostIntroductionAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e),
        )

        self.assertEqual(a.event_slug(), "test-event")

    def test_all_recipients(self):
        # totally fake Event
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            contact=TAG_SEPARATOR.join(["test@hogwart.com", "test2@magic.uk"]),
            country="GB",
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        # tasks
        Task.objects.create(person=self.person1, role=self.host, event=e)
        Task.objects.create(
            person=self.person2, role=self.instructor, event=e,
        )
        Task.objects.create(
            person=self.person3, role=self.instructor, event=e,
        )

        a = InstructorsHostIntroductionAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e),
        )

        self.assertEqual(
            a.all_recipients(),
            "hp@magic.uk, rw@magic.uk, hg@magic.uk, test@hogwart.com, test2@magic.uk",
        )
