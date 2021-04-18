from datetime import date, timedelta

from django.test import TestCase

from autoemails.actions import AskForWebsiteAction
from autoemails.models import EmailTemplate, Trigger
from workshops.models import Event, Organization, Person, Role, Tag, Task


class TestAskForWebsiteAction(TestCase):
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
        # used in AskForWebsiteAction
        Organization.objects.bulk_create(
            [
                Organization(domain="carpentries.org", fullname="Instructor Training"),
                Organization(
                    domain="librarycarpentry.org", fullname="Library Carpentry"
                ),
            ]
        )

    def testLaunchAt(self):
        e1 = Event(slug="test-event1", host=Organization.objects.first())
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
        e4 = Event(
            slug="test-event4",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=70),
            end=date.today() + timedelta(days=71),
        )

        # case 1: no context event
        a1 = AskForWebsiteAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
        )
        self.assertEqual(a1.get_launch_at(), timedelta(days=-30))

        # case 2: event with no start date
        a2 = AskForWebsiteAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e1),
        )
        self.assertEqual(a2.get_launch_at(), timedelta(days=-30))

        # case 3: event with near start date
        a3 = AskForWebsiteAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e2),
        )
        self.assertEqual(a3.get_launch_at(), timedelta(hours=1))

        # case 4: event with negative start date
        a4 = AskForWebsiteAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e3),
        )
        self.assertEqual(a4.get_launch_at(), timedelta(hours=1))

        # case 5: event with start date in 10 weeks
        a5 = AskForWebsiteAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e4),
        )
        self.assertEqual(a5.get_launch_at(), timedelta(days=40, hours=1))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake Task, Role and Event data
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="self-organized"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e.tags.set(Tag.objects.filter(name__in=["automated-email"]))
        p = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="instructor")
        s = Role.objects.create(name="supporting-instructor")
        t = Task.objects.create(event=e, person=p, role=r)

        # 1st case: everything is good
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # 2nd case: event has no end date
        # result: OK
        e.end = None
        e.save()
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # 3rd case: event has no start date
        # result: FAIL
        e.start = None
        e.save()
        self.assertEqual(AskForWebsiteAction.check(e), False)

        # bring back the good start date
        e.start = date.today() + timedelta(days=7)
        e.save()
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # 4th case: event is tagged with one (or more) excluding tags
        # result: FAIL
        for tag in ["cancelled", "stalled", "unresponsive"]:
            e.tags.add(Tag.objects.get(name=tag))
            self.assertEqual(AskForWebsiteAction.check(e), False)
            e.tags.remove(Tag.objects.get(name=tag))

        # retest to make sure it's back to normal
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # 5th case: not self-organized (centrally-organised)
        # result: OK
        e.administrator = Organization.objects.get(domain="carpentries.org")
        e.save()
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # retest to make sure it stays the same
        e.administrator = Organization.objects.get(domain="self-organized")
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # 6th case: website URL present
        # result: FAIL
        e.url = "http://example.org"
        e.save()
        self.assertEqual(AskForWebsiteAction.check(e), False)

        # retest to make sure it's back to normal
        e.url = ""
        e.save()
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # 7th case: no instructor tasks
        # result: FAIL
        r.name = "helper"
        r.save()
        self.assertEqual(AskForWebsiteAction.check(e), False)
        r.name = "instructor"
        r.save()

        # retest to make sure it's back to normal
        self.assertEqual(AskForWebsiteAction.check(e), True)

        # 8th case: supporting role used
        # result: OK
        t.role = s
        t.save()
        self.assertEqual(AskForWebsiteAction.check(e), True)

    def testContext(self):
        """Make sure `get_additional_context` works correctly."""
        a = AskForWebsiteAction(
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
            personal="Ron",
            family="Weasley",
            username="rweasley",
            email="rw@magic.uk",
        )
        instructor = Role.objects.create(name="instructor")
        supporting = Role.objects.create(name="supporting-instructor")
        host = Role.objects.create(name="host")
        Task.objects.create(event=e, person=p1, role=instructor)
        Task.objects.create(event=e, person=p2, role=supporting)
        Task.objects.create(event=e, person=p3, role=host)

        ctx = a.get_additional_context(objects=dict(event=e))
        self.assertEqual(
            ctx,
            dict(
                workshop=e,
                workshop_main_type="SWC",
                dates=e.human_readable_date,
                workshop_host=Organization.objects.first(),
                regional_coordinator_email=["admin-uk@carpentries.org"],
                instructors=[p1, p2],
                hosts=[p3],
                all_emails=["hp@magic.uk", "hg@magic.uk"],
                assignee="Regional Coordinator",
                tags=["SWC", "TTT"],
            ),
        )

    def testRecipients(self):
        """Make sure AskForWebsiteAction correctly renders recipients.

        They should get overwritten by AskForWebsiteAction during email
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
        instructor = Role.objects.create(name="instructor")
        supporting = Role.objects.create(name="supporting-instructor")
        Task.objects.bulk_create(
            [
                Task(event=e, person=p1, role=instructor),
                Task(event=e, person=p2, role=supporting),
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
            action="week-after-workshop-completion",
            template=template,
        )
        a = AskForWebsiteAction(
            trigger=trigger,
            objects=dict(event=e),
        )
        email = a._email()
        self.assertEqual(email.to, [p1.email, p2.email])

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

        a = AskForWebsiteAction(
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
        instructor = Role.objects.create(name="instructor")
        supporting = Role.objects.create(name="supporting-instructor")
        Task.objects.bulk_create(
            [
                Task(event=e, person=p1, role=instructor),
                Task(event=e, person=p2, role=supporting),
            ]
        )

        a = AskForWebsiteAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e),
        )

        self.assertEqual(
            a.all_recipients(),
            "hg@magic.uk, hp@magic.uk",
        )
