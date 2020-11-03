from datetime import timedelta, datetime

from django.test import TestCase

from autoemails.actions import GenericAction
from autoemails.models import Trigger, EmailTemplate
from workshops.models import (
    Event,
    Organization,
    Tag,
    WorkshopRequest,
    Task,
    Person,
    Role,
)


class TestGenericAction(TestCase):
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

        self.instructor_role = Role.objects.create(name="instructor")
        self.person1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", username="hp",
        )
        self.person2 = Person.objects.create(
            personal="Ron", family="Weasley", email="rw@magic.uk", username="rw",
        )

    def testLaunchAt(self):
        a1 = GenericAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
        )
        self.assertEqual(a1.get_launch_at(), timedelta(hours=1))

    def testCheckConditions(self):
        e = Event(slug="test-event1", host=Organization.objects.first())
        with self.assertRaises(NotImplementedError):
            GenericAction.check(e)

    def testContext(self):
        a = GenericAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'request' object
        with self.assertRaises(AttributeError):
            # impossible to access `assigned_to` on a string
            a.get_additional_context(dict(request="dummy"))
        with self.assertRaises(AttributeError):
            # impossible to access `refresh_from_db` on a string
            a.get_additional_context(dict(request="dummy", event="dummy"))

        wr = WorkshopRequest()
        ctx = a.get_additional_context(dict(request=wr))
        self.assertEqual(ctx, {"request": wr, "assignee": "Regional Coordinator"})

        event = Event.objects.create(
            slug="test-event1",
            host=Organization.objects.first(),
            start=datetime(2020, 10, 30),
            end=datetime(2020, 11, 1),
        )
        event.tags.set([Tag.objects.get(name="SWC")])
        ctx = a.get_additional_context(dict(request=wr, event=event))
        self.assertEqual(
            ctx,
            {
                "request": wr,
                "workshop": event,
                "workshop_main_type": "SWC",
                "dates": "Oct 30 - Nov 01, 2020",
                "workshop_host": Organization.objects.first(),
                "regional_coordinator_email": ["team@carpentries.org"],
                "all_emails": [],
                "assignee": "Regional Coordinator",
                "tags": ["SWC"],
            },
        )

    def testRecipients(self):
        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome to {{ site.name }}",
            to_header="{{ request.email }}",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="{{ reply_to }}",
            body_template="Sample text.",
        )
        trigger = Trigger.objects.create(
            action="workshop-request-response1", template=template,
        )
        wr = WorkshopRequest(email="test@email.com")
        event = Event.objects.create(
            slug="test-event1",
            host=Organization.objects.first(),
            start=datetime(2020, 10, 30),
            end=datetime(2020, 11, 1),
        )
        event.tags.set([Tag.objects.get(name="SWC")])
        a = GenericAction(trigger=trigger, objects=dict(request=wr, event=event))
        email = a._email()
        self.assertEqual(email.to, ["test@email.com"])

    def test_event_slug(self):
        wr = WorkshopRequest(email="test@email.com")
        event = Event.objects.create(
            slug="test-event1",
            host=Organization.objects.first(),
            start=datetime(2020, 10, 30),
            end=datetime(2020, 11, 1),
        )
        a = GenericAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(request=wr, event=event),
        )
        self.assertEqual(a.event_slug(), "test-event1")

    def test_all_recipients(self):
        wr = WorkshopRequest(email="test@email.com")
        e = Event.objects.create(
            slug="test-event1",
            host=Organization.objects.first(),
            start=datetime(2020, 10, 30),
            end=datetime(2020, 11, 1),
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

        a = GenericAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(request=wr, event=e),
        )

        self.assertEqual(
            a.all_recipients(), "test@email.com",
        )
