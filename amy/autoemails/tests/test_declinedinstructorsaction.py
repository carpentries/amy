from datetime import date, timedelta

from django.test import TestCase

from autoemails.actions import DeclinedInstructorsAction
from autoemails.models import EmailTemplate, Trigger
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.models import Event, Organization, Person, Tag
from workshops.util import human_daterange


class TestDeclinedInstructorsAction(TestCase):
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
        Organization.objects.bulk_create(
            [Organization(domain="carpentries.org", fullname="Instructor Training")]
        )

        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        self.event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        self.person = Person.objects.create(
            username="test1",
            personal="Test1",
            family="Test1",
            email="test1@example.org",
        )
        self.recruitment = InstructorRecruitment.objects.create(
            event=self.event, status="o"
        )

        self.template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome to {{ site.name }}",
            to_header="recipient@address.com",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="{{ reply_to }}",
            body_template="Sample text.",
        )
        self.trigger = Trigger.objects.create(
            action="self-organised-request-form",
            template=self.template,
        )

    def test_launch_at(self) -> None:
        a = DeclinedInstructorsAction(trigger=self.trigger)
        self.assertEqual(a.get_launch_at(), timedelta(hours=1))

    def test_check_conditions_fail(self) -> None:
        # Arrange
        event = Event.objects.create(
            slug="test-event2",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        recruitment_closed = InstructorRecruitment.objects.create(
            event=event, status="c"
        )
        signup1 = InstructorRecruitmentSignup(
            person=self.person, recruitment=self.recruitment, state="a"
        )
        signup2 = InstructorRecruitmentSignup(
            person=self.person, recruitment=recruitment_closed, state="a"
        )
        signup3 = InstructorRecruitmentSignup(
            person=self.person, recruitment=self.recruitment, state="d"
        )
        # Act & Assert
        self.assertFalse(DeclinedInstructorsAction.check(signup1))
        self.assertFalse(DeclinedInstructorsAction.check(signup2))
        self.assertFalse(DeclinedInstructorsAction.check(signup3))

    def test_check_conditions_pass(self) -> None:
        # Arrange
        event = Event.objects.create(
            slug="test-event2",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        recruitment_closed = InstructorRecruitment.objects.create(
            event=event, status="c"
        )
        signup = InstructorRecruitmentSignup(
            person=self.person, recruitment=recruitment_closed, state="d"
        )
        # Act &  Assert
        self.assertTrue(DeclinedInstructorsAction.check(signup))

    def test_context_missing_keys(self) -> None:
        # Arrange
        action = DeclinedInstructorsAction(
            trigger=self.trigger,
            objects=dict(
                recruitment=self.recruitment,
                event=self.recruitment.event,
                person=self.person,
            ),
        )
        # Act & Assert
        with self.assertRaises(KeyError):
            # missing recruitment
            action.get_additional_context({})
        with self.assertRaises(KeyError):
            # missing event
            action.get_additional_context({"recruitment": self.recruitment})
        with self.assertRaises(KeyError):
            # missing person
            action.get_additional_context(
                {"recruitment": self.recruitment, "event": self.event}
            )

        # OK
        action.get_additional_context(
            {
                "recruitment": self.recruitment,
                "event": self.event,
                "person": self.person,
            }
        )

    def test_context(self) -> None:
        # Arrange
        action = DeclinedInstructorsAction(
            trigger=self.trigger,
            objects=dict(
                recruitment=self.recruitment,
                event=self.recruitment.event,
                person=self.person,
            ),
        )
        # Act
        context = action.get_additional_context(
            {
                "recruitment": self.recruitment,
                "event": self.event,
                "person": self.person,
            }
        )
        # Assert
        self.maxDiff = None
        expected = {
            "assignee": "Regional Coordinator",
            "dates": human_daterange(self.event.start, self.event.end),
            "email": self.person.email,
            "host": self.event.host,
            "person": self.person,
            "recruitment": self.recruitment,
            "regional_coordinator_email": ["workshops@carpentries.org"],
            "tags": ["automated-email", "LC"],
            "workshop": self.event,
            "workshop_main_type": "LC",
        }
        self.assertEqual(context, expected)

    def test_recipients(self) -> None:
        # Arrange
        action = DeclinedInstructorsAction(
            trigger=self.trigger,
            objects=dict(
                recruitment=self.recruitment,
                event=self.recruitment.event,
                person=self.person,
            ),
        )
        # Act
        email = action._email()
        # Assert
        self.assertEqual(email.to, ["test1@example.org"])

    def test_event_slug(self) -> None:
        # Arrange
        action = DeclinedInstructorsAction(
            trigger=self.trigger,
            objects=dict(
                recruitment=self.recruitment,
                event=self.recruitment.event,
                person=self.person,
            ),
        )
        # Act
        slug = action.event_slug()
        # Assert
        self.assertEqual(slug, "test-event")

    def test_all_recipients(self) -> None:
        # Arrange
        action = DeclinedInstructorsAction(
            trigger=self.trigger,
            objects=dict(
                recruitment=self.recruitment,
                event=self.recruitment.event,
                person=self.person,
            ),
        )
        # Act
        emails = action.all_recipients()
        # Assert
        self.assertEqual(emails, "test1@example.org")
