from datetime import timedelta, date

from django.test import TestCase

from autoemails.actions import RecruitHelpersAction
from autoemails.models import Trigger, EmailTemplate
from workshops.models import Task, Role, Person, Event, Tag, Organization


class TestRecruitHelpersAction(TestCase):
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
        # by default there's only self-organized organization, but it can't be
        # used in RecruitHelpersAction
        Organization.objects.bulk_create(
            [
                Organization(domain="carpentries.org", fullname="Instructor Training"),
                Organization(
                    domain="librarycarpentry.org", fullname="Library Carpentry"
                ),
            ]
        )

        self.host_role = Role.objects.create(name="host")
        self.instructor_role = Role.objects.create(name="instructor")
        self.helper_role = Role.objects.create(name="helper")

        self.person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", username="hp",
        )
        self.person2 = Person.objects.create(
            personal="Ron", family="Weasley", email="rw@magic.uk", username="rw",
        )
        self.person3 = Person.objects.create(
            personal="Hermione", family="Granger", email="hg@magic.uk", username="hg",
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
        a1 = RecruitHelpersAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
        )
        self.assertEqual(a1.get_launch_at(), timedelta(days=-21))

        # case 2: event with no start date
        a2 = RecruitHelpersAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e1),
        )
        self.assertEqual(a2.get_launch_at(), timedelta(days=-21))

        # case 3: event with near start date
        a3 = RecruitHelpersAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e2),
        )
        self.assertEqual(a3.get_launch_at(), timedelta(hours=1))

        # case 4: event with negative start date
        a4 = RecruitHelpersAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e3),
        )
        self.assertEqual(a4.get_launch_at(), timedelta(hours=1))

        # case 5: event with start date in 10 weeks
        a5 = RecruitHelpersAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e4),
        )
        self.assertEqual(a5.get_launch_at(), timedelta(days=49, hours=1))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake Task, Role and Event data
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=30),
            end=date.today() + timedelta(days=31),
            administrator=Organization.objects.first(),
        )
        e.tags.set(Tag.objects.filter(name__in=["automated-email"]))
        Task.objects.bulk_create(
            [
                Task(event=e, person=self.person1, role=self.host_role),
                Task(event=e, person=self.person2, role=self.instructor_role),
            ]
        )

        # 1st case: everything is good
        self.assertEqual(RecruitHelpersAction.check(e), True)

        # 2nd case: event has no end date
        # result: OK
        e.end = None
        e.save()
        self.assertEqual(RecruitHelpersAction.check(e), True)

        # 3rd case: event has no start date
        # result: FAIL
        e.start = None
        e.save()
        self.assertEqual(RecruitHelpersAction.check(e), False)

        # bring back the good start date
        e.start = date.today() + timedelta(days=30)
        e.save()
        self.assertEqual(RecruitHelpersAction.check(e), True)

        # 4th case: event is tagged with one (or more) excluding tags
        # result: FAIL
        for tag in ["cancelled", "stalled", "unresponsive"]:
            e.tags.add(Tag.objects.get(name=tag))
            self.assertEqual(RecruitHelpersAction.check(e), False)
            e.tags.remove(Tag.objects.get(name=tag))

        # retest to make sure it's back to normal
        self.assertEqual(RecruitHelpersAction.check(e), True)

        # 5th case: more hosts and instructors
        # result: OK
        Task.objects.bulk_create(
            [
                Task(event=e, role=self.host_role, person=self.person2),
                Task(event=e, role=self.instructor_role, person=self.person1),
            ]
        )
        self.assertEqual(RecruitHelpersAction.check(e), True)

        # 6th case: no instructors nor hosts
        # result: FAIL
        Task.objects.filter(
            role__in=[self.host_role, self.instructor_role], event=e
        ).delete()
        self.assertEqual(RecruitHelpersAction.check(e), False)

        # bring back one instructor task
        Task.objects.create(event=e, person=self.person1, role=self.instructor_role)
        self.assertEqual(RecruitHelpersAction.check(e), True)

        # 7th case: helper task
        # result: FAIL
        helper = Task.objects.create(
            event=e, person=self.person2, role=self.helper_role
        )
        self.assertEqual(RecruitHelpersAction.check(e), False)
        helper.role = self.instructor_role
        helper.save()

        # retest to make sure it's back to normal
        self.assertEqual(RecruitHelpersAction.check(e), True)

        # 8th case: self-organised
        # result: FAIL
        e.administrator = Organization.objects.get(domain="self-organized")
        e.save()
        self.assertEqual(RecruitHelpersAction.check(e), False)
        e.administrator = Organization.objects.first()
        e.save()

        # retest to make sure it's back to normal
        self.assertEqual(RecruitHelpersAction.check(e), True)


    def testContext(self):
        """Make sure `get_additional_context` works correctly."""
        a = RecruitHelpersAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )

        # method fails when obligatory objects are missing
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'event'
        with self.assertRaises(AttributeError):
            # now both objects are present, but the method tries to execute
            # `refresh_from_db` on them
            a.get_additional_context(dict(event="dummy"))

        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
        )
        e.tags.set(Tag.objects.filter(name__in=["TTT", "SWC"]))
        Task.objects.create(event=e, person=self.person1, role=self.host_role)
        Task.objects.create(event=e, person=self.person2, role=self.instructor_role)

        ctx = a.get_additional_context(objects=dict(event=e))
        self.assertEqual(
            ctx,
            dict(
                workshop=e,
                workshop_main_type="SWC",
                dates=e.human_readable_date,
                workshop_host=Organization.objects.first(),
                regional_coordinator_email=["admin-uk@carpentries.org"],
                hosts=[self.person1],
                instructors=[self.person2],
                all_emails=["hp@magic.uk", "rw@magic.uk"],
                assignee="Regional Coordinator",
                tags=["SWC", "TTT"],
            ),
        )

    def testRecipients(self):
        """Make sure RecruitHelpersAction correctly renders recipients.

        They should get overwritten by RecruitHelpersAction during email
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
        Task.objects.bulk_create(
            [
                Task(event=e, person=self.person1, role=self.instructor_role),
                Task(event=e, person=self.person2, role=self.instructor_role),
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
        a = RecruitHelpersAction(trigger=trigger, objects=dict(event=e),)
        email = a._email()
        self.assertEqual(email.to, [self.person1.email, self.person2.email])

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
        t = Task.objects.create(event=e, person=self.person1, role=self.instructor_role)

        a = RecruitHelpersAction(
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
        Task.objects.bulk_create(
            [
                Task(event=e, person=self.person1, role=self.instructor_role),
                Task(event=e, person=self.person2, role=self.instructor_role),
            ]
        )

        a = RecruitHelpersAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e),
        )

        self.assertEqual(
            a.all_recipients(), "hp@magic.uk, rw@magic.uk",
        )
