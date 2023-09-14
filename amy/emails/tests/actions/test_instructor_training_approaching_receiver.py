from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions import instructor_training_approaching_receiver
from emails.models import EmailTemplate, ScheduledEmail
from emails.signals import instructor_training_approaching_signal
from workshops.models import Event, Organization, Person, Role, Tag, Task
from workshops.tests.base import TestBase


class TestInstructorTrainingApproachingReceiver(TestCase):
    @patch("workshops.utils.feature_flags.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            instructor_training_approaching_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping "
                "instructor_training_approaching_receiver"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_training_approaching_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_training_approaching_signal.connect(
            instructor_training_approaching_receiver
        )
        new_receivers = instructor_training_approaching_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_training_approaching_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        ttt_tag = Tag.objects.create(name="TTT")
        event.tags.add(ttt_tag)
        instructor_role = Role.objects.create(name="instructor")
        instructor1 = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )
        instructor2 = Person.objects.create(
            personal="Test", family="Test", email="test2@example.org", username="test2"
        )
        Task.objects.create(event=event, person=instructor1, role=instructor_role)
        Task.objects.create(event=event, person=instructor2, role=instructor_role)

        # Act
        with patch(
            "emails.actions.instructor_training_approaching.messages_action_scheduled"
        ) as mock_messages_action_scheduled:
            instructor_training_approaching_signal.send(
                sender=event,
                request=request,
                event=event,
                event_start_date=event.start,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_scheduled.assert_called_once_with(
            request,
            instructor_training_approaching_signal.signal_name,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.instructor_training_approaching.messages_action_scheduled")
    @patch("emails.actions.instructor_training_approaching.one_month_before")
    def test_email_scheduled(
        self,
        mock_one_month_before: MagicMock,
        mock_messages_action_scheduled: MagicMock,
    ) -> None:
        # Arrange
        ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date(2023, 9, 4),
        )
        ttt_tag = Tag.objects.create(name="TTT")
        event.tags.add(ttt_tag)
        instructor_role = Role.objects.create(name="instructor")
        instructor1 = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )
        instructor2 = Person.objects.create(
            personal="Test", family="Test", email="test2@example.org", username="test2"
        )
        Task.objects.create(event=event, person=instructor1, role=instructor_role)
        Task.objects.create(event=event, person=instructor2, role=instructor_role)

        request = RequestFactory().get("/")
        signal = instructor_training_approaching_signal.signal_name
        context = {"event": event, "instructors": [instructor1, instructor2]}
        scheduled_at = datetime(2023, 8, 5, 12, 0, tzinfo=UTC)
        mock_one_month_before.return_value = scheduled_at

        # Act
        with patch(
            "emails.actions.persons_merged.EmailController.schedule_email"
        ) as mock_schedule_email:
            instructor_training_approaching_signal.send(
                sender=event,
                request=request,
                event=event,
                event_start_date=event.start,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[instructor1.email, instructor2.email],
            generic_relation_obj=event,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.instructor_training_approaching.messages_missing_recipients")
    def test_missing_recipients(
        self, mock_messages_missing_recipients: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")

        ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        ttt_tag = Tag.objects.create(name="TTT")
        event.tags.add(ttt_tag)
        instructor_role = Role.objects.create(name="instructor")
        instructor1 = Person.objects.create(
            personal="Test", family="Test", username="test1"
        )
        instructor2 = Person.objects.create(
            personal="Test", family="Test", username="test2"
        )
        Task.objects.create(event=event, person=instructor1, role=instructor_role)
        Task.objects.create(event=event, person=instructor2, role=instructor_role)
        signal = instructor_training_approaching_signal.signal_name

        # Act
        instructor_training_approaching_signal.send(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.instructor_training_approaching.messages_missing_template")
    def test_missing_template(self, mock_messages_missing_template: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")

        ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        ttt_tag = Tag.objects.create(name="TTT")
        event.tags.add(ttt_tag)
        instructor_role = Role.objects.create(name="instructor")
        instructor1 = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )
        instructor2 = Person.objects.create(
            personal="Test", family="Test", email="test2@example.org", username="test2"
        )
        Task.objects.create(event=event, person=instructor1, role=instructor_role)
        Task.objects.create(event=event, person=instructor2, role=instructor_role)
        signal = instructor_training_approaching_signal.signal_name

        # Act
        instructor_training_approaching_signal.send(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

        # Assert
        mock_messages_missing_template.assert_called_once_with(request, signal)


class TestInstructorTrainingApproachingReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_training_approaching_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        ttt_tag = Tag.objects.get(name="TTT")
        event.tags.add(ttt_tag)

        instructor1 = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        instructor2 = Person.objects.create(
            personal="Jayden",
            middle="",
            family="Deckow",
            username="deckow_jayden",
            email="deckow.jayden@example.com",
            secondary_email="notused@example.org",
            gender="M",
            airport=self.airport_0_50,
            github="deckow_jayden",
            twitter="deckow_jayden",
            url="http://jaydendeckow.com/",
            affiliation="UFlo",
            occupation="Staff",
            orcid="0000-0000-0001",
            is_active=True,
        )
        instructor_role = Role.objects.get(name="instructor")
        Task.objects.create(event=event, person=instructor1, role=instructor_role)

        url = reverse("task_add")
        payload = {
            "task-event": event.pk,
            "task-person": instructor2.pk,
            "task-role": instructor_role.pk,
        }

        # Act
        rv = self.client.post(url, data=payload)

        # Arrange
        self.assertEqual(rv.status_code, 302)
        ScheduledEmail.objects.get(template=template)
