from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, call, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from src.emails.actions.instructor_training_approaching import (
    instructor_training_approaching_cancel_receiver,
    instructor_training_approaching_strategy,
    run_instructor_training_approaching_strategy,
)
from src.emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from src.emails.signals import (
    INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
    instructor_training_approaching_cancel_signal,
)
from src.workshops.models import Event, Organization, Person, Role, Tag, Task
from src.workshops.tests.base import TestBase


class TestInstructorTrainingApproachingCancelReceiver(TestCase):
    def setUp(self) -> None:
        self.ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=self.ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        ttt_tag = Tag.objects.create(name="TTT")
        self.event.tags.add(ttt_tag)
        instructor_role = Role.objects.create(name="instructor")
        self.instructor1 = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )
        self.instructor2 = Person.objects.create(
            personal="Test", family="Test", email="test2@example.org", username="test2"
        )
        Task.objects.create(event=self.event, person=self.instructor1, role=instructor_role)
        Task.objects.create(event=self.event, person=self.instructor2, role=instructor_role)

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    @patch("src.emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            instructor_training_approaching_cancel_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping instructor_training_approaching_cancel"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_training_approaching_cancel_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_training_approaching_cancel_signal.connect(instructor_training_approaching_cancel_receiver)
        new_receivers = instructor_training_approaching_cancel_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        request = RequestFactory().get("/")

        template = self.setUpEmailTemplate()
        scheduled_email = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )

        # Act
        with patch("src.emails.actions.base_action.messages_action_cancelled") as mock_messages_action_cancelled:
            instructor_training_approaching_cancel_signal.send(
                sender=self.event,
                request=request,
                event=self.event,
                event_start_date=self.event.start,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_cancelled.assert_called_once_with(
            request,
            INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_action_cancelled")
    def test_email_cancelled(
        self,
        mock_messages_action_cancelled: MagicMock,
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        scheduled_email = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )

        # Act
        with patch("src.emails.actions.base_action.EmailController.cancel_email") as mock_cancel_email:
            instructor_training_approaching_cancel_signal.send(
                sender=self.event,
                request=request,
                event=self.event,
                event_start_date=self.event.start,
            )

        # Assert
        mock_cancel_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_action_cancelled")
    def test_multiple_emails_cancelled(
        self,
        mock_messages_action_cancelled: MagicMock,
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        scheduled_email1 = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )
        scheduled_email2 = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )

        # Act
        with patch("src.emails.actions.base_action.EmailController.cancel_email") as mock_cancel_email:
            instructor_training_approaching_cancel_signal.send(
                sender=self.event,
                request=request,
                event=self.event,
                event_start_date=self.event.start,
            )

        # Assert
        mock_cancel_email.assert_has_calls(
            [
                call(
                    scheduled_email=scheduled_email1,
                    author=None,
                ),
                call(
                    scheduled_email=scheduled_email2,
                    author=None,
                ),
            ]
        )


class TestInstructorTrainingApproachingCancelIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
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
            airport_iata="CDG",
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            bluesky="@purdy_kelsi.bsky.social",
            mastodon="https://mastodon.social/@sdfgh",
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
            airport_iata="LAX",
            github="deckow_jayden",
            twitter="deckow_jayden",
            bluesky="@deckow_jayden.bsky.social",
            mastodon="http://jaydendeckow.com/",
            url="http://jaydendeckow.com/",
            affiliation="UFlo",
            occupation="Staff",
            orcid="0000-0000-0001",
            is_active=True,
        )
        instructor_role = Role.objects.get(name="instructor")
        Task.objects.create(event=event, person=instructor1, role=instructor_role)
        task = Task.objects.create(event=event, person=instructor2, role=instructor_role)
        request = RequestFactory().get("/")

        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_instructor_training_approaching_strategy(
                instructor_training_approaching_strategy(event),
                request,
                event,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("task_delete", args=[task.pk])

        # Act
        rv = self.client.post(url)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
