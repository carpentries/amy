from datetime import timedelta, date

from django.test import TestCase

from autoemails.actions import PostWorkshopAction
from autoemails.models import Trigger, EmailTemplate
from workshops.fields import TAG_SEPARATOR
from workshops.models import Task, Role, Person, Event, Tag, Organization


class TestPostWorkshopAction(TestCase):
    def setUp(self):
        # we're missing some tags
        Tag.objects.bulk_create(
            [
                Tag(name="automated-email", priority=0),
                Tag(name="SWC", priority=10),
                Tag(name="DC", priority=20),
                Tag(name="LC", priority=30),
                Tag(name="TTT", priority=40),
            ]
        )
        # by default there's only self-organized organization, but it can't be
        # used in PostWorkshopAction
        Organization.objects.bulk_create(
            [
                Organization(domain="carpentries.org", fullname="Instructor Training"),
                Organization(
                    domain="librarycarpentry.org", fullname="Library Carpentry"
                ),
            ]
        )

    def testLaunchAt(self):
        e1 = Event(slug="test-event1", host=Organization.objects.first(),)
        e2 = Event(
            slug="test-event2",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e3 = Event(
            slug="test-event3",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=-8),
            end=date.today() + timedelta(days=-7),
        )

        # case 1: no context event
        a1 = PostWorkshopAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
        )
        self.assertEqual(a1.get_launch_at(), timedelta(days=7))

        # case 2: event with no end date
        a2 = PostWorkshopAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e1),
        )
        self.assertEqual(a2.get_launch_at(), timedelta(days=7))

        # case 3: event with end date
        a3 = PostWorkshopAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e2),
        )
        self.assertEqual(a3.get_launch_at(), timedelta(days=8 + 7))

        # case 4: event with negative end date
        a4 = PostWorkshopAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e3),
        )
        self.assertEqual(a4.get_launch_at(), timedelta(days=7))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake Task, Role and Event data
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="librarycarpentry.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "TTT", "automated-email"]))
        p = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="host")
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
        for tag in ["cancelled", "stalled", "unresponsive"]:
            e.tags.add(Tag.objects.get(name=tag))
            self.assertEqual(PostWorkshopAction.check(e), False)
            e.tags.remove(Tag.objects.get(name=tag))

        # retest to make sure it's back to normal
        self.assertEqual(PostWorkshopAction.check(e), True)

        # 5th case: no host/instructor tasks
        # This is tricky case. Sometimes the workshop can be defined before
        # there are any instructor/host tasks.
        # result: OK
        r.name = "helper"
        r.save()
        self.assertEqual(PostWorkshopAction.check(e), True)
        r.name = "instructor"  # additionally check for instructor role
        r.save()

        # retest to make sure it's back to normal
        # (note: role was changed to "instructor")
        self.assertEqual(PostWorkshopAction.check(e), True)

        # 6th case: wrong administrator (Instructor Training)
        # result: FAIL
        e.administrator = Organization.objects.get(domain="carpentries.org")
        e.save()
        self.assertEqual(PostWorkshopAction.check(e), False)

        # retest to make sure it's back to normal
        e.administrator = Organization.objects.get(domain="librarycarpentry.org")
        self.assertEqual(PostWorkshopAction.check(e), True)

    def testCheckConditionsCircuits(self):
        """Make sure `check` works for "Circuits" workshops too."""
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="librarycarpentry.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e.tags.set(Tag.objects.filter(name__in=["automated-email"]))
        p = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="host")
        Task.objects.create(event=e, person=p, role=r)

        # 1st case: fail
        self.assertEqual(PostWorkshopAction.check(e), False)

        # 2nd case: success
        e.tags.add(Tag.objects.get(name="Circuits"))
        self.assertEqual(PostWorkshopAction.check(e), True)

    def testContext(self):
        """Make sure `get_additional_context` works correctly."""
        a = PostWorkshopAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )

        # method fails when obligatory objects are missing
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'event'
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
            # additionally testing the empty email
            contact=TAG_SEPARATOR.join(["peter@webslinger.net", ""])
        )
        e.tags.set(Tag.objects.filter(name__in=["TTT", "SWC"]))
        p1 = Person.objects.create(
            personal="Harry", family="Potter", username="hpotter", email="hp@magic.uk"
        )
        p2 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            username="hgranger",
            email="hg@magic.uk",
        )
        p3 = Person.objects.create(
            personal="Ron", family="Weasley", username="rweasley", email="rw@magic.uk"
        )
        p4 = Person.objects.create(
            personal="Draco", family="Malfoy", username="dmalfoy",
            email="draco@malfoy.com"
        )
        host = Role.objects.create(name="host")
        instructor = Role.objects.create(name="instructor")
        helper = Role.objects.create(name="helper")
        supporting_instructor = Role.objects.create(name="supporting-instructor")
        Task.objects.bulk_create(
            [
                Task(event=e, person=p1, role=host),
                Task(event=e, person=p2, role=instructor),
                Task(event=e, person=p3, role=helper),
                Task(event=e, person=p1, role=helper),
                Task(event=e, person=p4, role=supporting_instructor),
            ]
        )

        ctx = a.get_additional_context(objects=dict(event=e))
        self.assertEqual(
            ctx,
            dict(
                workshop=e,
                workshop_main_type="SWC",
                dates=e.human_readable_date,
                host=Organization.objects.first(),
                regional_coordinator_email=["admin-uk@carpentries.org"],
                instructors=[p2],
                supporting_instructors=[p4],
                helpers=[p1, p3],
                all_emails=[
                    "hg@magic.uk",
                    "draco@malfoy.com",
                    "hp@magic.uk",
                    "peter@webslinger.net",
                ],
                assignee="Regional Coordinator",
                reports_link="https://workshop-reports.carpentries.org/"
                             "?key=e18dd84d093be5cd6c6ccaf63d38a8477ca126f4"
                             "&slug=test-event",
                tags=['SWC', 'TTT'],
            ),
        )

    def testRecipients(self):
        """Make sure PostWorkshopAction correctly renders recipients.

        They should get overwritten by PostWorkshopAction during email
        building."""
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
        )
        e.tags.set(Tag.objects.filter(name="LC"))
        p1 = Person.objects.create(
            personal="Harry", family="Potter", username="hpotter", email="hp@magic.uk"
        )
        p2 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            username="hgranger",
            email="hg@magic.uk",
        )
        p3 = Person.objects.create(
            personal="Ron", family="Weasley", username="rweasley", email="rw@magic.uk"
        )
        p4 = Person.objects.create(
            personal="Draco", family="Malfoy", username="dmalfoy",
            email="draco@malfoy.com"
        )
        host = Role.objects.create(name="host")
        instructor = Role.objects.create(name="instructor")
        supporting_instructor = Role.objects.create(name="supporting-instructor")
        Task.objects.bulk_create(
            [
                Task(event=e, person=p1, role=instructor),
                Task(event=e, person=p2, role=instructor),
                Task(event=e, person=p3, role=host),
                Task(event=e, person=p1, role=host),
                Task(event=e, person=p4, role=supporting_instructor),
            ]
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
            action="week-after-workshop-completion", template=template,
        )
        a = PostWorkshopAction(trigger=trigger, objects=dict(event=e),)
        email = a._email()
        self.assertEqual(email.to, [p2.email, p4.email, p1.email, p3.email])

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
        p1 = Person.objects.create(
            personal="Harry", family="Potter", username="hpotter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="instructor")
        t = Task.objects.create(event=e, person=p1, role=r)

        a = PostWorkshopAction(
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
        )
        e.tags.set(Tag.objects.filter(name="LC"))
        p1 = Person.objects.create(
            personal="Harry", family="Potter", username="hpotter", email="hp@magic.uk"
        )
        p2 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            username="hgranger",
            email="hg@magic.uk",
        )
        p3 = Person.objects.create(
            personal="Ron", family="Weasley", username="rweasley", email="rw@magic.uk"
        )
        p4 = Person.objects.create(
            personal="Draco", family="Malfoy", username="dmalfoy",
            email="draco@malfoy.com"
        )
        host = Role.objects.create(name="host")
        instructor = Role.objects.create(name="instructor")
        supporting_instructor = Role.objects.create(name="supporting-instructor")
        Task.objects.bulk_create(
            [
                Task(event=e, person=p1, role=instructor),
                Task(event=e, person=p2, role=instructor),
                Task(event=e, person=p3, role=host),
                Task(event=e, person=p1, role=host),
                Task(event=e, person=p4, role=supporting_instructor),
            ]
        )

        a = PostWorkshopAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e),
        )

        self.assertEqual(a.all_recipients(), "hg@magic.uk, draco@malfoy.com, hp@magic.uk, rw@magic.uk")
